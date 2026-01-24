"""Routing engine service - interfaces with Valhalla."""

import uuid
from typing import List, Optional, Tuple

import httpx

from app.config import settings
from app.schemas.routing import (
    RouteRequest,
    RouteResponse,
    RoutePreferences,
    RouteProfile,
    VehicleType,
    RouteSummary,
    RouteLeg,
    Maneuver,
    ManeuverType,
    BikeLaneStatus,
    RouteRiskAnalysis,
    GeoJSONLineString,
)
from app.schemas.common import Coordinate


# Mapping from Valhalla maneuver types to our types
VALHALLA_MANEUVER_MAP = {
    0: ManeuverType.DEPART,
    1: ManeuverType.DEPART,
    2: ManeuverType.STRAIGHT,
    3: ManeuverType.SLIGHT_RIGHT,
    4: ManeuverType.TURN_RIGHT,
    5: ManeuverType.TURN_RIGHT,  # Sharp right
    6: ManeuverType.U_TURN,
    7: ManeuverType.U_TURN,
    8: ManeuverType.SLIGHT_LEFT,
    9: ManeuverType.TURN_LEFT,
    10: ManeuverType.TURN_LEFT,  # Sharp left
    11: ManeuverType.U_TURN,
    12: ManeuverType.U_TURN,
    13: ManeuverType.STRAIGHT,  # Ramp straight
    14: ManeuverType.SLIGHT_RIGHT,  # Ramp right
    15: ManeuverType.SLIGHT_LEFT,  # Ramp left
    16: ManeuverType.MERGE,  # Exit right
    17: ManeuverType.MERGE,  # Exit left
    18: ManeuverType.STRAIGHT,  # Stay straight
    19: ManeuverType.SLIGHT_RIGHT,  # Stay right
    20: ManeuverType.SLIGHT_LEFT,  # Stay left
    21: ManeuverType.MERGE,
    22: ManeuverType.ROUNDABOUT,  # Enter roundabout
    23: ManeuverType.ROUNDABOUT,  # Exit roundabout
    24: ManeuverType.FORK,  # Ferry enter
    25: ManeuverType.FORK,  # Ferry exit
    26: ManeuverType.ARRIVE,
    27: ManeuverType.ARRIVE,
}


class RoutingEngine:
    """Service for calculating routes using Valhalla."""

    def __init__(self):
        self.valhalla_url = settings.valhalla_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def calculate_route(
        self,
        request: RouteRequest,
    ) -> RouteResponse:
        """Calculate a route between two points."""

        # Build Valhalla request
        valhalla_request = self._build_valhalla_request(request)

        # Call Valhalla API
        try:
            response = await self.client.post(
                f"{self.valhalla_url}/route",
                json=valhalla_request,
            )
            response.raise_for_status()
            valhalla_response = response.json()
        except httpx.HTTPStatusError as e:
            # Handle Valhalla errors
            raise ValueError(f"Routing failed: {e.response.text}")
        except httpx.RequestError as e:
            raise ValueError(f"Could not connect to routing engine: {str(e)}")

        # Parse response into our format
        return self._parse_valhalla_response(valhalla_response, request)

    async def calculate_alternatives(
        self,
        request: RouteRequest,
        num_alternatives: int = 3,
    ) -> List[RouteResponse]:
        """Calculate multiple alternative routes."""

        routes = []

        # Calculate routes with different profiles
        profiles = [RouteProfile.SAFEST, RouteProfile.FASTEST, RouteProfile.BALANCED]

        for profile in profiles[:num_alternatives]:
            modified_request = request.model_copy()
            modified_request.preferences.profile = profile

            try:
                route = await self.calculate_route(modified_request)
                routes.append(route)
            except ValueError:
                continue

        return routes

    def _build_valhalla_request(self, request: RouteRequest) -> dict:
        """Build Valhalla API request from our request model."""

        # Map vehicle type to Valhalla costing
        costing_map = {
            VehicleType.SCOOTER: "bicycle",  # Treat scooter like bicycle
            VehicleType.BIKE: "bicycle",
            VehicleType.EBIKE: "bicycle",
        }
        costing = costing_map.get(request.vehicle_type, "bicycle")

        # Build costing options based on preferences
        costing_options = self._build_costing_options(
            request.preferences, request.vehicle_type
        )

        return {
            "locations": [
                {
                    "lat": request.origin.latitude,
                    "lon": request.origin.longitude,
                    "type": "break",
                },
                {
                    "lat": request.destination.latitude,
                    "lon": request.destination.longitude,
                    "type": "break",
                },
            ],
            "costing": costing,
            "costing_options": {costing: costing_options},
            "directions_options": {
                "units": "meters",
                "language": "en-US",
            },
            "format": "json",
        }

    def _build_costing_options(
        self, preferences: RoutePreferences, vehicle_type: VehicleType
    ) -> dict:
        """Build Valhalla costing options from preferences."""

        options = {
            "bicycle_type": "Road" if vehicle_type == VehicleType.BIKE else "Hybrid",
            "use_roads": 0.5,  # Balance between roads and bike paths
            "use_hills": 0.5 if not preferences.avoid_hills else 0.1,
            "avoid_bad_surfaces": 0.5,
        }

        # Adjust based on profile
        if preferences.profile == RouteProfile.SAFEST:
            options["use_roads"] = 0.2  # Prefer bike paths
            options["use_hills"] = 0.3
            options["avoid_bad_surfaces"] = 0.8
        elif preferences.profile == RouteProfile.FASTEST:
            options["use_roads"] = 0.7  # Allow more road usage
            options["use_hills"] = 0.7  # Accept hills for shorter routes
            options["avoid_bad_surfaces"] = 0.3
        elif preferences.profile == RouteProfile.SCENIC:
            options["use_roads"] = 0.3
            options["use_hills"] = 0.4
            options["avoid_bad_surfaces"] = 0.6

        # Bike lane preference
        if preferences.prefer_bike_lanes:
            options["use_roads"] = min(
                options["use_roads"], 1 - preferences.bike_lane_weight
            )

        return options

    def _parse_valhalla_response(
        self, response: dict, request: RouteRequest
    ) -> RouteResponse:
        """Parse Valhalla response into our format."""

        trip = response.get("trip", {})
        legs = trip.get("legs", [])

        if not legs:
            raise ValueError("No route found")

        # Extract summary
        summary = trip.get("summary", {})

        # Build geometry from legs
        all_coordinates = []
        parsed_legs = []

        for leg in legs:
            shape = leg.get("shape", "")
            leg_coords = self._decode_polyline(shape)
            all_coordinates.extend(leg_coords)

            # Parse maneuvers
            maneuvers = []
            for m in leg.get("maneuvers", []):
                maneuver = self._parse_maneuver(m)
                maneuvers.append(maneuver)

            parsed_legs.append(
                RouteLeg(
                    geometry=GeoJSONLineString(coordinates=leg_coords),
                    distance_meters=int(leg.get("summary", {}).get("length", 0) * 1000),
                    duration_seconds=int(leg.get("summary", {}).get("time", 0)),
                    maneuvers=maneuvers,
                )
            )

        # Calculate route summary
        route_summary = RouteSummary(
            distance_meters=int(summary.get("length", 0) * 1000),  # km to m
            duration_seconds=int(summary.get("time", 0)),
            elevation_gain_meters=0,  # Would need elevation data
            elevation_loss_meters=0,
            max_grade_percent=0,
            bike_lane_percentage=0,  # Would need to analyze route segments
            risk_score=0,
        )

        return RouteResponse(
            route_id=uuid.uuid4(),
            geometry=GeoJSONLineString(coordinates=all_coordinates),
            summary=route_summary,
            legs=parsed_legs,
            risk_analysis=RouteRiskAnalysis(),
            warnings=[],
        )

    def _parse_maneuver(self, m: dict) -> Maneuver:
        """Parse a Valhalla maneuver into our format."""

        maneuver_type = VALHALLA_MANEUVER_MAP.get(
            m.get("type", 0), ManeuverType.STRAIGHT
        )

        begin_shape_index = m.get("begin_shape_index", 0)
        # Note: We'd need the decoded shape to get exact coordinates
        # For now, use a placeholder

        return Maneuver(
            type=maneuver_type,
            instruction=m.get("instruction", ""),
            verbal_instruction=m.get("verbal_pre_transition_instruction", m.get("instruction", "")),
            location=Coordinate(latitude=0, longitude=0),  # Would extract from shape
            distance_meters=int(m.get("length", 0) * 1000),
            street_name=m.get("street_names", [None])[0] if m.get("street_names") else None,
            bike_lane_status=BikeLaneStatus.NONE,
            alerts=[],
        )

    def _decode_polyline(self, encoded: str, precision: int = 6) -> List[List[float]]:
        """Decode a polyline string into a list of coordinates.

        Valhalla uses precision 6 by default.
        """
        coordinates = []
        index = 0
        lat = 0
        lng = 0

        while index < len(encoded):
            # Decode latitude
            shift = 0
            result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            dlat = ~(result >> 1) if result & 1 else result >> 1
            lat += dlat

            # Decode longitude
            shift = 0
            result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            dlng = ~(result >> 1) if result & 1 else result >> 1
            lng += dlng

            # Add coordinate [lon, lat] for GeoJSON
            coordinates.append([lng / (10**precision), lat / (10**precision)])

        return coordinates

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
routing_engine = RoutingEngine()
