"""Routing request and response schemas."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import Coordinate, GeoJSONLineString


class VehicleType(str, Enum):
    """Type of micromobility vehicle."""

    SCOOTER = "scooter"
    BIKE = "bike"
    EBIKE = "ebike"


class RouteProfile(str, Enum):
    """Route optimization profile."""

    SAFEST = "safest"
    FASTEST = "fastest"
    BALANCED = "balanced"
    SCENIC = "scenic"


class RoutePreferences(BaseModel):
    """User preferences for route calculation."""

    profile: RouteProfile = Field(
        default=RouteProfile.BALANCED,
        description="Route optimization profile",
    )
    avoid_hills: bool = Field(
        default=False,
        description="Avoid steep hills",
    )
    max_grade_percent: float = Field(
        default=15.0,
        ge=0,
        le=30,
        description="Maximum acceptable grade percentage",
    )
    prefer_bike_lanes: bool = Field(
        default=True,
        description="Prefer routes with bike lanes",
    )
    bike_lane_weight: float = Field(
        default=0.7,
        ge=0,
        le=1,
        description="Weight for bike lane preference (0=ignore, 1=strongly prefer)",
    )


class RouteRequest(BaseModel):
    """Request body for route calculation."""

    origin: Coordinate = Field(..., description="Starting point")
    destination: Coordinate = Field(..., description="Ending point")
    vehicle_type: VehicleType = Field(
        default=VehicleType.SCOOTER,
        description="Type of vehicle",
    )
    preferences: RoutePreferences = Field(
        default_factory=RoutePreferences,
        description="Route preferences",
    )
    avoid_risk_zones: bool = Field(
        default=True,
        description="Avoid known risk zones when possible",
    )
    departure_time: Optional[datetime] = Field(
        default=None,
        description="Departure time for traffic prediction",
    )


class ManeuverType(str, Enum):
    """Types of navigation maneuvers."""

    DEPART = "depart"
    ARRIVE = "arrive"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    SLIGHT_LEFT = "slight_left"
    SLIGHT_RIGHT = "slight_right"
    STRAIGHT = "straight"
    U_TURN = "u_turn"
    MERGE = "merge"
    FORK = "fork"
    ROUNDABOUT = "roundabout"


class BikeLaneStatus(str, Enum):
    """Status of bike lane along route segment."""

    ENTERING = "entering"
    LEAVING = "leaving"
    CONTINUING = "continuing"
    NONE = "none"


class ManeuverAlert(BaseModel):
    """Alert associated with a maneuver."""

    type: str = Field(..., description="Alert type (risk_zone, steep_hill, etc.)")
    message: str = Field(..., description="Alert message")
    severity: str = Field(..., description="Alert severity")


class Maneuver(BaseModel):
    """Turn-by-turn navigation instruction."""

    type: ManeuverType = Field(..., description="Maneuver type")
    instruction: str = Field(..., description="Human-readable instruction")
    verbal_instruction: str = Field(..., description="TTS-friendly instruction")
    location: Coordinate = Field(..., description="Location of maneuver")
    distance_meters: int = Field(..., ge=0, description="Distance to next maneuver")
    street_name: Optional[str] = Field(None, description="Name of street")
    bike_lane_status: BikeLaneStatus = Field(
        default=BikeLaneStatus.NONE,
        description="Bike lane status change",
    )
    alerts: List[ManeuverAlert] = Field(
        default_factory=list,
        description="Alerts at this maneuver",
    )


class RouteLeg(BaseModel):
    """A leg of the route."""

    geometry: GeoJSONLineString = Field(..., description="Leg geometry")
    distance_meters: int = Field(..., ge=0, description="Leg distance")
    duration_seconds: int = Field(..., ge=0, description="Leg duration")
    maneuvers: List[Maneuver] = Field(
        default_factory=list,
        description="Maneuvers in this leg",
    )


class RouteSummary(BaseModel):
    """Summary statistics for a route."""

    distance_meters: int = Field(..., ge=0, description="Total distance")
    duration_seconds: int = Field(..., ge=0, description="Total duration")
    elevation_gain_meters: int = Field(
        default=0, ge=0, description="Total elevation gain"
    )
    elevation_loss_meters: int = Field(
        default=0, ge=0, description="Total elevation loss"
    )
    max_grade_percent: float = Field(
        default=0, description="Maximum grade on route"
    )
    bike_lane_percentage: float = Field(
        default=0,
        ge=0,
        le=100,
        description="Percentage of route on bike infrastructure",
    )
    risk_score: float = Field(
        default=0,
        ge=0,
        le=1,
        description="Overall route risk (0=safest, 1=highest risk)",
    )


class RouteRiskAnalysis(BaseModel):
    """Risk analysis for a route."""

    total_risk_zones: int = Field(default=0, description="Number of risk zones on route")
    high_severity_zones: int = Field(default=0, description="High/critical severity zones")
    risk_zone_ids: List[UUID] = Field(
        default_factory=list,
        description="IDs of risk zones on route",
    )


class RouteWarning(BaseModel):
    """Warning about the route."""

    type: str = Field(..., description="Warning type")
    message: str = Field(..., description="Warning message")
    location: Optional[Coordinate] = Field(None, description="Location if applicable")


class RouteResponse(BaseModel):
    """Response for route calculation."""

    route_id: UUID = Field(..., description="Unique route identifier")
    geometry: GeoJSONLineString = Field(..., description="Route geometry")
    summary: RouteSummary = Field(..., description="Route summary")
    legs: List[RouteLeg] = Field(default_factory=list, description="Route legs")
    risk_analysis: RouteRiskAnalysis = Field(
        default_factory=RouteRiskAnalysis,
        description="Risk analysis",
    )
    warnings: List[RouteWarning] = Field(
        default_factory=list,
        description="Route warnings",
    )


class RouteComparison(BaseModel):
    """Comparison of multiple routes."""

    fastest_index: int = Field(..., description="Index of fastest route")
    safest_index: int = Field(..., description="Index of safest route")
    recommended_index: int = Field(..., description="Index of recommended route")
