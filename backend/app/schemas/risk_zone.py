"""Risk zone schemas."""

from datetime import datetime, time
from typing import List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.risk_zone import HazardType, HazardSeverity, DataSource
from app.schemas.common import Coordinate


class RiskZoneBase(BaseModel):
    """Base schema for risk zones."""

    hazard_type: HazardType
    severity: HazardSeverity = HazardSeverity.MEDIUM
    name: Optional[str] = None
    description: Optional[str] = None
    is_permanent: bool = True
    alert_radius_meters: int = Field(default=50, ge=10, le=500)
    alert_message: Optional[str] = None


class RiskZoneCreate(RiskZoneBase):
    """Schema for creating a risk zone."""

    location: Coordinate = Field(..., description="Point location of hazard")


class RiskZoneResponse(RiskZoneBase):
    """Schema for risk zone response."""

    id: UUID
    geometry: Any = Field(..., description="GeoJSON geometry")
    source: DataSource
    confidence_score: float
    reported_count: int
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NearbyRiskZone(BaseModel):
    """Risk zone with distance information."""

    risk_zone: RiskZoneResponse
    distance_meters: float = Field(..., description="Distance from query point")


class NearbyRiskZonesResponse(BaseModel):
    """Response for nearby risk zones query."""

    zones: List[NearbyRiskZone]
    total: int
    query_location: Coordinate
    query_radius_meters: int


class RouteRiskZone(BaseModel):
    """Risk zone along a route."""

    risk_zone: RiskZoneResponse
    distance_along_route_meters: float = Field(
        ..., description="Distance from route start"
    )


class RouteRiskZonesResponse(BaseModel):
    """Response for risk zones along a route."""

    zones: List[RouteRiskZone]
    total: int
