"""Hazard Report database model for user-submitted reports."""

import enum
import uuid
from datetime import datetime
from typing import Optional, List

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    Enum,
    Integer,
    Numeric,
    String,
    Text,
    DateTime,
    ARRAY,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.risk_zone import HazardType, HazardSeverity


class ReportStatus(str, enum.Enum):
    """Status of a hazard report."""

    PENDING = "pending"
    VERIFIED = "verified"
    MERGED = "merged"
    REJECTED = "rejected"
    RESOLVED = "resolved"


class HazardReport(Base):
    """User-submitted hazard report."""

    __tablename__ = "hazard_reports"

    # Location
    location: Mapped[str] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
    )
    accuracy_meters: Mapped[Optional[float]] = mapped_column(
        Numeric(8, 2), nullable=True
    )

    # Classification
    hazard_type: Mapped[HazardType] = mapped_column(
        Enum(HazardType),
        nullable=False,
    )
    severity: Mapped[HazardSeverity] = mapped_column(
        Enum(HazardSeverity),
        default=HazardSeverity.MEDIUM,
    )

    # User input
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo_urls: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(Text), nullable=True
    )

    # Device/session info (anonymous tracking)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Processing
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus),
        default=ReportStatus.PENDING,
    )
    merged_into_zone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("risk_zones.id"),
        nullable=True,
    )
    verification_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ReportVerification(Base):
    """Verification of a hazard report by another user."""

    __tablename__ = "report_verifications"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hazard_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )
