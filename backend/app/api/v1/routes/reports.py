"""Hazard Reporting API endpoints."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.hazard_report import HazardReport, ReportStatus, ReportVerification
from app.models.risk_zone import HazardType, HazardSeverity
from app.schemas.common import Coordinate

router = APIRouter()


class HazardReportRequest:
    """Request schema for hazard report submission."""

    def __init__(
        self,
        location: Coordinate,
        hazard_type: HazardType,
        session_id: UUID,
        accuracy_meters: Optional[float] = None,
        severity: HazardSeverity = HazardSeverity.MEDIUM,
        description: Optional[str] = None,
        device_type: Optional[str] = None,
    ):
        self.location = location
        self.hazard_type = hazard_type
        self.session_id = session_id
        self.accuracy_meters = accuracy_meters
        self.severity = severity
        self.description = description
        self.device_type = device_type


@router.post("")
async def submit_hazard_report(
    location: Coordinate,
    hazard_type: HazardType,
    session_id: UUID,
    accuracy_meters: Optional[float] = None,
    severity: HazardSeverity = HazardSeverity.MEDIUM,
    description: Optional[str] = None,
    device_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Submit a new hazard report.

    Users can report hazards they encounter while riding.
    Reports are initially pending and may be verified by other users.
    """
    # Create point geometry
    point = Point(location.longitude, location.latitude)

    # Create report
    report = HazardReport(
        location=from_shape(point, srid=4326),
        accuracy_meters=accuracy_meters,
        hazard_type=hazard_type,
        severity=severity,
        description=description,
        session_id=session_id,
        device_type=device_type,
        status=ReportStatus.PENDING,
        reported_at=datetime.utcnow(),
    )

    db.add(report)
    await db.commit()
    await db.refresh(report)

    return {
        "id": str(report.id),
        "status": report.status.value,
        "message": "Report submitted successfully",
        "reported_at": report.reported_at.isoformat(),
    }


@router.post("/{report_id}/verify")
async def verify_report(
    report_id: UUID,
    is_confirmed: bool,
    session_id: UUID,
    location: Optional[Coordinate] = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Verify or dispute a hazard report.

    Other users can confirm or dispute reported hazards.
    Reports with enough verifications become confirmed risk zones.
    """
    # Check if report exists
    result = await db.execute(
        select(HazardReport).where(HazardReport.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.status not in [ReportStatus.PENDING, ReportStatus.VERIFIED]:
        raise HTTPException(
            status_code=400, detail="Report cannot be verified in current status"
        )

    # Check if user already verified
    existing = await db.execute(
        select(ReportVerification).where(
            and_(
                ReportVerification.report_id == report_id,
                ReportVerification.session_id == session_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="You have already verified this report"
        )

    # Create verification
    verification_location = None
    if location:
        verification_location = from_shape(
            Point(location.longitude, location.latitude), srid=4326
        )

    verification = ReportVerification(
        report_id=report_id,
        session_id=session_id,
        is_confirmed=is_confirmed,
        location=verification_location,
    )

    db.add(verification)

    # Update verification count
    if is_confirmed:
        report.verification_count += 1

        # Auto-verify if enough confirmations (threshold: 3)
        if report.verification_count >= 3 and report.status == ReportStatus.PENDING:
            report.status = ReportStatus.VERIFIED
            report.verified_at = datetime.utcnow()
            # TODO: Create risk zone from verified report

    await db.commit()

    return {
        "report_id": str(report_id),
        "verification_recorded": True,
        "is_confirmed": is_confirmed,
        "total_verifications": report.verification_count,
        "status": report.status.value,
    }


@router.get("/nearby")
async def get_nearby_reports(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius: int = Query(200, ge=50, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get pending reports near a location that user could verify.
    """
    # TODO: Implement spatial query for nearby pending reports

    return {
        "reports": [],
        "total": 0,
        "message": "Nearby reports query not yet fully implemented",
    }


@router.get("/{report_id}")
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get details of a specific report.
    """
    result = await db.execute(
        select(HazardReport).where(HazardReport.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": str(report.id),
        "hazard_type": report.hazard_type.value,
        "severity": report.severity.value,
        "description": report.description,
        "status": report.status.value,
        "verification_count": report.verification_count,
        "reported_at": report.reported_at.isoformat(),
        "verified_at": report.verified_at.isoformat() if report.verified_at else None,
    }
