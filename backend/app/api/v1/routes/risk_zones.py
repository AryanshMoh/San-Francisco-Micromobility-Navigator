"""Risk Zones API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_MakePoint, ST_SetSRID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.risk_zone import RiskZone, HazardSeverity
from app.schemas.risk_zone import (
    RiskZoneResponse,
    NearbyRiskZone,
    NearbyRiskZonesResponse,
)
from app.schemas.common import Coordinate, BoundingBox, GeoJSONLineString

router = APIRouter()


@router.get("", response_model=List[RiskZoneResponse])
async def get_risk_zones(
    bbox: str = Query(
        ...,
        description="Bounding box as minLon,minLat,maxLon,maxLat",
        example="-122.52,37.70,-122.35,37.82",
    ),
    severity: Optional[HazardSeverity] = Query(
        None, description="Filter by minimum severity"
    ),
    types: Optional[str] = Query(
        None, description="Filter by hazard types (comma-separated)"
    ),
    db: AsyncSession = Depends(get_db),
) -> List[RiskZoneResponse]:
    """
    Get all active risk zones within a bounding box.
    """
    try:
        bounds = BoundingBox.from_string(bbox)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Build query
    query = select(RiskZone).where(RiskZone.is_active == True)

    # TODO: Add spatial filter using ST_Within or ST_Intersects with bbox

    # Filter by severity
    if severity:
        severity_order = [HazardSeverity.LOW, HazardSeverity.MEDIUM, HazardSeverity.HIGH, HazardSeverity.CRITICAL]
        min_severity_idx = severity_order.index(severity)
        allowed_severities = severity_order[min_severity_idx:]
        query = query.where(RiskZone.severity.in_(allowed_severities))

    # Filter by types
    if types:
        type_list = [t.strip() for t in types.split(",")]
        query = query.where(RiskZone.hazard_type.in_(type_list))

    result = await db.execute(query.limit(500))
    zones = result.scalars().all()

    # Convert to response format
    return [_zone_to_response(zone) for zone in zones]


@router.get("/near", response_model=NearbyRiskZonesResponse)
async def get_risk_zones_near(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius: int = Query(100, ge=10, le=1000, description="Search radius in meters"),
    db: AsyncSession = Depends(get_db),
) -> NearbyRiskZonesResponse:
    """
    Get risk zones within a specified radius of a point.
    """
    # Build point geometry
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    # Query for nearby zones with distance
    query = (
        select(
            RiskZone,
            ST_Distance(
                RiskZone.geometry.cast_to_geography(),
                point.cast_to_geography()
            ).label("distance")
        )
        .where(
            and_(
                RiskZone.is_active == True,
                ST_DWithin(
                    RiskZone.geometry.cast_to_geography(),
                    point.cast_to_geography(),
                    radius
                )
            )
        )
        .order_by("distance")
    )

    result = await db.execute(query)
    rows = result.all()

    zones = [
        NearbyRiskZone(
            risk_zone=_zone_to_response(row.RiskZone),
            distance_meters=row.distance,
        )
        for row in rows
    ]

    return NearbyRiskZonesResponse(
        zones=zones,
        total=len(zones),
        query_location=Coordinate(latitude=lat, longitude=lon),
        query_radius_meters=radius,
    )


@router.post("/along-route")
async def get_risk_zones_along_route(
    route_geometry: GeoJSONLineString,
    buffer_meters: int = Query(30, ge=10, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get risk zones that a route passes through or near.
    """
    # TODO: Implement spatial query for route buffer
    # This would use ST_Buffer on the route and ST_Intersects with risk zones

    return {
        "zones": [],
        "total": 0,
        "message": "Route risk zone query not yet implemented",
    }


@router.get("/{zone_id}", response_model=RiskZoneResponse)
async def get_risk_zone(
    zone_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> RiskZoneResponse:
    """
    Get details of a specific risk zone.
    """
    result = await db.execute(select(RiskZone).where(RiskZone.id == zone_id))
    zone = result.scalar_one_or_none()

    if not zone:
        raise HTTPException(status_code=404, detail="Risk zone not found")

    return _zone_to_response(zone)


def _zone_to_response(zone: RiskZone) -> RiskZoneResponse:
    """Convert a RiskZone model to response schema."""
    from shapely import wkb
    from shapely.geometry import mapping

    # Convert geometry to GeoJSON
    try:
        # Parse WKB geometry
        geom = wkb.loads(bytes(zone.geometry.data))
        geometry_geojson = mapping(geom)
    except Exception:
        geometry_geojson = {"type": "Point", "coordinates": [0, 0]}

    return RiskZoneResponse(
        id=zone.id,
        geometry=geometry_geojson,
        hazard_type=zone.hazard_type,
        severity=zone.severity,
        name=zone.name,
        description=zone.description,
        is_permanent=zone.is_permanent,
        alert_radius_meters=zone.alert_radius_meters,
        alert_message=zone.alert_message,
        source=zone.source,
        confidence_score=float(zone.confidence_score),
        reported_count=zone.reported_count,
        is_active=zone.is_active,
        created_at=zone.created_at,
        expires_at=zone.expires_at,
    )
