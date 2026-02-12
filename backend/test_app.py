"""Standalone test app without database dependencies."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
import uuid

app = FastAPI(
    title="SF Micromobility Navigation API (Test Mode)",
    description="Testing API structure without database",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Schemas
class Coordinate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class RouteProfile(str, Enum):
    SAFEST = "safest"
    FASTEST = "fastest"
    BALANCED = "balanced"


class RoutePreferences(BaseModel):
    profile: RouteProfile = RouteProfile.BALANCED
    avoid_hills: bool = False
    prefer_bike_lanes: bool = True
    bike_lane_weight: float = Field(default=0.7, ge=0, le=1)


class RouteRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate
    vehicle_type: str = "scooter"
    preferences: RoutePreferences = RoutePreferences()


class RouteSummary(BaseModel):
    distance_meters: int
    duration_seconds: int
    elevation_gain_meters: int = 0
    elevation_loss_meters: int = 0
    max_grade_percent: float = 0
    bike_lane_percentage: float = 0
    risk_score: float = 0


class RiskAnalysis(BaseModel):
    total_risk_zones: int = 0
    high_severity_zones: int = 0
    risk_zone_ids: List[str] = []


class RouteResponse(BaseModel):
    route_id: str
    geometry: dict
    summary: RouteSummary
    risk_analysis: RiskAnalysis = RiskAnalysis()


class HazardType(str, Enum):
    POTHOLE = "pothole"
    DANGEROUS_INTERSECTION = "dangerous_intersection"
    CONSTRUCTION = "construction"
    STEEP_GRADE = "steep_grade"
    TROLLEY_TRACKS = "trolley_tracks"


class HazardSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskZone(BaseModel):
    id: str
    geometry: dict
    hazard_type: HazardType
    severity: HazardSeverity
    name: Optional[str] = None
    alert_message: Optional[str] = None


# Mock data
MOCK_RISK_ZONES = [
    RiskZone(
        id="rz-001",
        geometry={"type": "Point", "coordinates": [-122.4194, 37.7749]},
        hazard_type=HazardType.POTHOLE,
        severity=HazardSeverity.MEDIUM,
        name="Market St Pothole",
        alert_message="Pothole ahead. Use caution.",
    ),
    RiskZone(
        id="rz-002",
        geometry={"type": "Point", "coordinates": [-122.4089, 37.7833]},
        hazard_type=HazardType.TROLLEY_TRACKS,
        severity=HazardSeverity.HIGH,
        name="Powell St Trolley Tracks",
        alert_message="Trolley tracks ahead. Cross at an angle.",
    ),
    RiskZone(
        id="rz-003",
        geometry={"type": "Point", "coordinates": [-122.4367, 37.7598]},
        hazard_type=HazardType.STEEP_GRADE,
        severity=HazardSeverity.MEDIUM,
        name="Twin Peaks Climb",
        alert_message="Steep hill ahead. 15% grade.",
    ),
]


# Endpoints
@app.get("/")
async def root():
    return {
        "name": "SF Micromobility Navigation API",
        "version": "1.0.0",
        "status": "Test Mode (no database)",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "mode": "test"}


@app.post("/api/v1/routes/calculate", response_model=RouteResponse)
async def calculate_route(request: RouteRequest):
    """Calculate a route (mock response for testing)."""

    # Create a simple straight-line route for testing
    coordinates = [
        [request.origin.longitude, request.origin.latitude],
        [request.destination.longitude, request.destination.latitude],
    ]

    # Estimate distance (rough approximation)
    lat_diff = abs(request.destination.latitude - request.origin.latitude)
    lon_diff = abs(request.destination.longitude - request.origin.longitude)
    distance_deg = (lat_diff**2 + lon_diff**2) ** 0.5
    distance_meters = int(distance_deg * 111000)  # ~111km per degree

    # Estimate duration (assume 15 km/h average for scooter)
    duration_seconds = int(distance_meters / 15000 * 3600)

    # Mock bike lane percentage based on profile
    bike_lane_pct = {
        RouteProfile.SAFEST: 85,
        RouteProfile.FASTEST: 40,
        RouteProfile.BALANCED: 65,
    }.get(request.preferences.profile, 65)

    # Mock risk analysis
    risk_zones_count = 1 if request.preferences.profile == RouteProfile.SAFEST else 2

    return RouteResponse(
        route_id=str(uuid.uuid4()),
        geometry={
            "type": "LineString",
            "coordinates": coordinates,
        },
        summary=RouteSummary(
            distance_meters=distance_meters,
            duration_seconds=duration_seconds,
            elevation_gain_meters=50 if not request.preferences.avoid_hills else 10,
            elevation_loss_meters=30 if not request.preferences.avoid_hills else 5,
            max_grade_percent=8 if not request.preferences.avoid_hills else 3,
            bike_lane_percentage=bike_lane_pct,
            risk_score=0.1 if request.preferences.profile == RouteProfile.SAFEST else 0.3 if request.preferences.profile == RouteProfile.BALANCED else 0.5,
        ),
        risk_analysis=RiskAnalysis(
            total_risk_zones=risk_zones_count,
            high_severity_zones=1 if risk_zones_count > 1 else 0,
            risk_zone_ids=["rz-001"] if risk_zones_count == 1 else ["rz-001", "rz-002"],
        ),
    )


@app.get("/api/v1/risk-zones", response_model=List[RiskZone])
async def get_risk_zones(
    bbox: Optional[str] = None,
    severity: Optional[HazardSeverity] = None,
):
    """Get risk zones (mock data for testing)."""
    zones = MOCK_RISK_ZONES

    if severity:
        severity_order = [HazardSeverity.LOW, HazardSeverity.MEDIUM, HazardSeverity.HIGH, HazardSeverity.CRITICAL]
        min_idx = severity_order.index(severity)
        zones = [z for z in zones if severity_order.index(z.severity) >= min_idx]

    return zones


@app.get("/api/v1/risk-zones/{zone_id}", response_model=RiskZone)
async def get_risk_zone(zone_id: str):
    """Get a specific risk zone."""
    for zone in MOCK_RISK_ZONES:
        if zone.id == zone_id:
            return zone
    raise HTTPException(status_code=404, detail="Risk zone not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
