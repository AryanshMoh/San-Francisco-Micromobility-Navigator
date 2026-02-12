"""Routing engine service - interfaces with Valhalla."""

import uuid
import logging
from typing import List, Optional, Tuple, Dict, Any

import math

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
from app.services.bike_lanes import bike_lane_service
from app.services.risk_zone_service import risk_zone_service, RiskZoneServiceError

logger = logging.getLogger(__name__)


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
        self._fallback_routes = []

    async def calculate_route(
        self,
        request: RouteRequest,
    ) -> RouteResponse:
        """Calculate a route between two points."""

        # For SAFEST profile with prefer_bike_lanes, use bike-lane-optimized routing
        if request.preferences.profile == RouteProfile.SAFEST:
            if request.preferences.prefer_bike_lanes:
                return await self._calculate_bike_lane_preferred_route(request)
            return await self._calculate_safest_route(request, min_severity="LOW")

        # For BALANCED profile, only avoid HIGH and CRITICAL zones
        if request.preferences.profile == RouteProfile.BALANCED:
            return await self._calculate_safest_route(request, min_severity="HIGH")

        # For FASTEST, try multiple candidates and pick the one with lowest duration
        return await self._calculate_fastest_route(request)

    async def _calculate_bike_lane_preferred_route(
        self, request: RouteRequest
    ) -> RouteResponse:
        """Calculate a route that prefers bike lanes while avoiding risk zones.

        This is used when the "Prefer Bike Lanes" toggle is enabled on the SAFEST profile.
        It tries to achieve at least 60% bike lane usage (or 70% if base route was 60-70%),
        while still respecting risk zone avoidance.

        Strategy:
        1. First calculate a standard safest route to get baseline
        2. Try multiple costing options that favor bike infrastructure
        3. Select the route with highest bike lane % that still avoids risk zones
        4. Prefer routes with efficient paths (not excessive distance for marginal % gain)
        """
        logger.info("Calculating SAFEST route with bike lane preference")

        # Get risk zones for validation
        all_zones = await risk_zone_service.get_risk_zones()
        risk_zones_data = risk_zone_service.filter_zones_by_severity(all_zones, "LOW")

        # Get exclude polygons for risk zone avoidance
        polygon_batches = await risk_zone_service.get_exclude_polygon_batches(
            buffer_multiplier=1.5,
            min_severity="LOW",
        )

        # Use first batch if available (covers most critical zones)
        exclude_polygons = polygon_batches[0] if polygon_batches else None

        # Try multiple costing options that increasingly favor bike lanes
        bike_lane_options = [
            # Most aggressive bike lane preference
            {"bicycle_type": "Hybrid", "use_roads": 0.0, "use_hills": 0.3, "avoid_bad_surfaces": 0.8},
            # Strong bike lane preference
            {"bicycle_type": "Road", "use_roads": 0.1, "use_hills": 0.3, "avoid_bad_surfaces": 0.7},
            # Moderate bike lane preference
            {"bicycle_type": "Hybrid", "use_roads": 0.2, "use_hills": 0.4, "avoid_bad_surfaces": 0.6},
            # Balanced but leaning toward bike lanes
            {"bicycle_type": "Cross", "use_roads": 0.3, "use_hills": 0.4, "avoid_bad_surfaces": 0.6},
        ]

        candidates = []
        avoidance_factor = 0.25  # SAFEST profile zone avoidance radius

        for idx, options in enumerate(bike_lane_options):
            try:
                valhalla_request = self._build_base_valhalla_request(request, options)
                if exclude_polygons:
                    valhalla_request["exclude_polygons"] = exclude_polygons

                response = await self.client.post(
                    f"{self.valhalla_url}/route",
                    json=valhalla_request,
                )
                if not response.is_success:
                    logger.debug(f"Bike lane option {idx} failed: HTTP {response.status_code}")
                    continue

                valhalla_response = response.json()
                route = await self._parse_valhalla_response(valhalla_response, request)

                if not route.geometry.coordinates:
                    continue

                # Validate against risk zones
                is_valid, violation_count, _ = risk_zone_service.validate_route_against_zones(
                    route.geometry.coordinates, all_zones, "LOW",
                    radius_factor=avoidance_factor,
                )

                bike_pct = route.summary.bike_lane_percentage
                distance = route.summary.distance_meters
                duration = route.summary.duration_seconds

                logger.debug(
                    f"Bike lane candidate {idx}: valid={is_valid}, "
                    f"bike_lane={bike_pct:.1f}%, dist={distance}m, time={duration}s"
                )

                candidates.append({
                    "route": route,
                    "is_valid": is_valid,
                    "violations": violation_count,
                    "bike_pct": bike_pct,
                    "distance": distance,
                    "duration": duration,
                })

            except Exception as e:
                logger.debug(f"Bike lane option {idx} failed: {e}")
                continue

        # Also try with alternates to get more options
        try:
            alt_request = self._build_base_valhalla_request(request, bike_lane_options[0])
            alt_request["alternates"] = 2
            if exclude_polygons:
                alt_request["exclude_polygons"] = exclude_polygons

            response = await self.client.post(
                f"{self.valhalla_url}/route",
                json=alt_request,
            )
            if response.is_success:
                valhalla_response = response.json()
                for trip_data in [valhalla_response] + valhalla_response.get("alternates", []):
                    try:
                        route = await self._parse_valhalla_response(trip_data, request)
                        if route.geometry.coordinates:
                            is_valid, violation_count, _ = risk_zone_service.validate_route_against_zones(
                                route.geometry.coordinates, all_zones, "LOW",
                                radius_factor=avoidance_factor,
                            )
                            candidates.append({
                                "route": route,
                                "is_valid": is_valid,
                                "violations": violation_count,
                                "bike_pct": route.summary.bike_lane_percentage,
                                "distance": route.summary.distance_meters,
                                "duration": route.summary.duration_seconds,
                            })
                    except Exception:
                        continue
        except Exception as e:
            logger.debug(f"Bike lane alternates failed: {e}")

        if not candidates:
            logger.warning("No bike lane candidates found, falling back to standard safest")
            return await self._calculate_safest_route(request, min_severity="LOW")

        # Filter to valid routes first (no risk zone violations)
        valid_candidates = [c for c in candidates if c["is_valid"]]

        if valid_candidates:
            # Among valid routes, pick the one with highest bike lane % that's reasonably efficient
            # We use a scoring function: bike_pct - (distance_penalty)
            # This prevents picking a 5-mile detour for 5% more bike lanes
            min_distance = min(c["distance"] for c in valid_candidates)

            def score_candidate(c):
                # Penalty for excessive distance (reduce score by 5% per 10% extra distance)
                distance_ratio = c["distance"] / min_distance if min_distance > 0 else 1
                distance_penalty = max(0, (distance_ratio - 1) * 50)  # 50% penalty per 100% extra distance
                return c["bike_pct"] - distance_penalty

            best = max(valid_candidates, key=score_candidate)
            logger.info(
                f"Selected bike lane preferred route: {best['bike_pct']:.1f}% bike lanes, "
                f"{best['distance']}m, VALID (0 zone violations)"
            )
            return best["route"]

        # If no completely valid routes, pick best of invalid ones
        # (least violations + highest bike lane %)
        candidates.sort(key=lambda c: (c["violations"], -c["bike_pct"]))
        best = candidates[0]
        logger.warning(
            f"No completely clean bike lane route, using least-bad: "
            f"{best['bike_pct']:.1f}% bike lanes, {best['violations']} zone violations"
        )
        return best["route"]

    async def _calculate_safest_route(
        self, request: RouteRequest, min_severity: str = "LOW"
    ) -> RouteResponse:
        """Calculate a route that avoids risk zones.

        Uses a multi-stage approach:
        1. Try exclude_polygons with Valhalla (batched if needed)
        2. Validate all candidates against zone constraints
        3. Only accept routes with ZERO forbidden-zone passes
        4. If no clean route found, use waypoint-based avoidance

        Args:
            request: Route request
            min_severity: Minimum zone severity to avoid
                - "LOW": Avoid all zones (SAFEST profile)
                - "HIGH": Only avoid HIGH and CRITICAL zones (BALANCED profile)
        """
        profile_name = "SAFEST" if min_severity == "LOW" else "BALANCED"
        logger.info(f"Calculating {profile_name} route (min_severity={min_severity})")

        all_zones = await risk_zone_service.get_risk_zones()
        risk_zones_data = risk_zone_service.filter_zones_by_severity(all_zones, min_severity)
        logger.info(f"Considering {len(risk_zones_data)} zones (filtered from {len(all_zones)})")

        if not risk_zones_data:
            return await self._calculate_basic_safest(request)

        # Stage 1: Get batched exclude polygons covering ALL relevant zones
        polygon_batches = await risk_zone_service.get_exclude_polygon_batches(
            buffer_multiplier=1.5,
            min_severity=min_severity,
        )
        logger.info(f"Created {len(polygon_batches)} exclude polygon batches for {profile_name}")

        route_options = [
            {"bicycle_type": "Road", "use_roads": 0.5, "use_hills": 0.3, "avoid_bad_surfaces": 0.5},
            {"bicycle_type": "Hybrid", "use_roads": 0.4, "use_hills": 0.4, "avoid_bad_surfaces": 0.6},
            {"bicycle_type": "Cross", "use_roads": 0.6, "use_hills": 0.5, "avoid_bad_surfaces": 0.4},
            {"bicycle_type": "Hybrid", "use_roads": 0.2, "use_hills": 0.3, "avoid_bad_surfaces": 0.7},
            {"bicycle_type": "Road", "use_roads": 0.3, "use_hills": 0.2, "avoid_bad_surfaces": 0.8},
        ]

        # Stage 2: Generate candidates using each batch of exclude polygons
        valid_routes = []
        all_candidates = []

        for batch_idx, batch_polygons in enumerate(polygon_batches):
            for opt_idx, options in enumerate(route_options):
                req = self._build_base_valhalla_request(request, options)
                req["exclude_polygons"] = batch_polygons
                all_candidates.append((f"batch{batch_idx}_opt{opt_idx}", req))

            # Also request alternates for this batch
            alt_req = self._build_base_valhalla_request(request, route_options[0])
            alt_req["alternates"] = 2
            alt_req["exclude_polygons"] = batch_polygons
            all_candidates.append((f"batch{batch_idx}_alts", alt_req))

        # If there's only one batch, also try with shortest=True
        if len(polygon_batches) == 1:
            shortest_opts = {"bicycle_type": "Road", "use_roads": 0.3, "use_hills": 0.2, "avoid_bad_surfaces": 0.5, "shortest": True}
            req = self._build_base_valhalla_request(request, shortest_opts)
            req["exclude_polygons"] = polygon_batches[0]
            all_candidates.append(("shortest", req))

        # Evaluate all candidates
        fallback_routes = []

        for name, valhalla_request in all_candidates:
            try:
                response = await self.client.post(
                    f"{self.valhalla_url}/route",
                    json=valhalla_request,
                )
                if not response.is_success:
                    logger.debug(f"Candidate '{name}' failed: HTTP {response.status_code}")
                    continue

                valhalla_response = response.json()
                trips = [("main", valhalla_response)]
                for i, alt in enumerate(valhalla_response.get("alternates", [])):
                    trips.append((f"alt{i}", alt))

                for trip_name, trip_data in trips:
                    try:
                        route = await self._parse_valhalla_response(trip_data, request)
                        if not route.geometry.coordinates:
                            continue

                        # Hard validation: check route against forbidden zone cores
                        # SAFEST uses 0.5x radius (avoid zone cores + visual match)
                        # BALANCED uses 0.4x radius (avoid worst spots)
                        avoidance_factor = 0.25 if min_severity == "LOW" else 0.2
                        is_valid, violation_count, _ = risk_zone_service.validate_route_against_zones(
                            route.geometry.coordinates, all_zones, min_severity,
                            radius_factor=avoidance_factor,
                        )
                        risk_score, zone_passes, zones_passed = risk_zone_service.calculate_route_risk_score(
                            route.geometry.coordinates, risk_zones_data
                        )
                        distance = route.summary.distance_meters

                        logger.debug(
                            f"Candidate '{name}_{trip_name}': valid={is_valid}, "
                            f"violations={violation_count}, passes={zone_passes}, dist={distance}m"
                        )

                        if is_valid:
                            valid_routes.append((route, distance, risk_score))
                        else:
                            fallback_routes.append((route, zone_passes, risk_score, distance))

                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"Candidate '{name}' failed: {e}")
                continue

        # Stage 2.5: Focused re-routing targeting specific violated zones
        if not valid_routes and fallback_routes:
            # Find which zones are most frequently violated across all candidates
            violation_counts: Dict[str, int] = {}
            for fb_route, fb_passes, fb_risk, fb_dist in fallback_routes:
                _, _, fb_violations = risk_zone_service.validate_route_against_zones(
                    fb_route.geometry.coordinates, all_zones, min_severity,
                    radius_factor=avoidance_factor,
                )
                for v in fb_violations:
                    zid = v["zone_id"]
                    violation_counts[zid] = violation_counts.get(zid, 0) + 1

            if violation_counts:
                violated_zone_ids = sorted(
                    violation_counts, key=lambda k: violation_counts[k], reverse=True
                )
                violated_zones = [
                    z for z in risk_zones_data if z.get("id") in set(violated_zone_ids)
                ]

                # Create focused exclude polygons with larger radii (3x avoidance radius)
                focused_polygons = []
                total_circ = 0.0
                for zone in violated_zones:
                    radius = zone["radius_meters"] * avoidance_factor * 3.0
                    circ = 2 * math.pi * radius
                    if total_circ + circ > 9500:
                        break
                    polygon = risk_zone_service.create_circular_polygon(
                        zone["lon"], zone["lat"], radius, num_points=8
                    )
                    focused_polygons.append(polygon)
                    total_circ += circ

                if focused_polygons:
                    logger.info(
                        f"Focused exclusion: {len(focused_polygons)} polygons "
                        f"for violated zones (circ={total_circ:.0f}m)"
                    )
                    for options in route_options:
                        req = self._build_base_valhalla_request(request, options)
                        req["exclude_polygons"] = focused_polygons
                        try:
                            response = await self.client.post(
                                f"{self.valhalla_url}/route", json=req,
                            )
                            if not response.is_success:
                                continue
                            valhalla_response = response.json()
                            for trip_data in [valhalla_response] + valhalla_response.get("alternates", []):
                                try:
                                    route = await self._parse_valhalla_response(trip_data, request)
                                    if not route.geometry.coordinates:
                                        continue
                                    is_valid, vc, _ = risk_zone_service.validate_route_against_zones(
                                        route.geometry.coordinates, all_zones, min_severity,
                                        radius_factor=avoidance_factor,
                                    )
                                    if is_valid:
                                        valid_routes.append((route, route.summary.distance_meters, 0))
                                    elif vc < fallback_routes[0][1]:
                                        fallback_routes.append((route, vc, 0, route.summary.distance_meters))
                                except Exception:
                                    continue
                        except Exception:
                            continue

                    # Also try with alternates
                    alt_req = self._build_base_valhalla_request(request, route_options[0])
                    alt_req["alternates"] = 2
                    alt_req["exclude_polygons"] = focused_polygons
                    try:
                        response = await self.client.post(
                            f"{self.valhalla_url}/route", json=alt_req,
                        )
                        if response.is_success:
                            valhalla_response = response.json()
                            for trip_data in [valhalla_response] + valhalla_response.get("alternates", []):
                                try:
                                    route = await self._parse_valhalla_response(trip_data, request)
                                    if route.geometry.coordinates:
                                        is_valid, _, _ = risk_zone_service.validate_route_against_zones(
                                            route.geometry.coordinates, all_zones, min_severity,
                                            radius_factor=avoidance_factor,
                                        )
                                        if is_valid:
                                            valid_routes.append((route, route.summary.distance_meters, 0))
                                except Exception:
                                    continue
                    except Exception:
                        pass

                    # Re-sort fallbacks if we added better ones
                    if fallback_routes:
                        fallback_routes.sort(key=lambda x: (x[1], x[2]))

        # Stage 3: Pick best valid route (zero forbidden-zone passes)
        if valid_routes:
            valid_routes.sort(key=lambda x: x[1])
            best = valid_routes[0]
            logger.info(f"Selected {profile_name} route: CLEAN (0 zone passes), dist={best[1]}m")
            return best[0]

        # Stage 4: Iterative waypoint avoidance targeting specific violated zones
        logger.info(f"No clean route from exclude_polygons, trying iterative avoidance")

        # Start from the best fallback candidate and iteratively fix violations
        if fallback_routes:
            fallback_routes.sort(key=lambda x: (x[1], x[2]))
            best_fallback = fallback_routes[0]
            iterative_result = await self._iterative_zone_avoidance(
                request, best_fallback[0], risk_zones_data, all_zones, min_severity
            )
            if iterative_result:
                return iterative_result

        # Stage 5: Broad waypoint avoidance
        waypoint_route = await self._try_waypoint_avoidance(request, risk_zones_data, all_zones, min_severity)
        if waypoint_route:
            return waypoint_route

        # Stage 6: Last resort — pick the candidate with fewest violations
        logger.warning(f"No completely clean {profile_name} route found, using least-bad candidate")
        if fallback_routes:
            return fallback_routes[0][0]

        return await self._calculate_basic_safest(request)

    async def _iterative_zone_avoidance(
        self, request: RouteRequest, current_route: RouteResponse,
        risk_zones_data: list, all_zones: list, min_severity: str,
        max_iterations: int = 5
    ) -> Optional[RouteResponse]:
        """Iteratively re-route to avoid specific violated zones.

        Takes the best candidate route, finds which zones it violates,
        then adds waypoints to route around those specific zones.
        Uses route-local perpendicular directions and focused exclude polygons.
        """
        best_route = current_route
        best_violations = float('inf')

        avoidance_factor = 0.25 if min_severity == "LOW" else 0.2

        for iteration in range(max_iterations):
            # Check which zones are violated
            is_valid, violation_count, violations = risk_zone_service.validate_route_against_zones(
                best_route.geometry.coordinates, all_zones, min_severity,
                radius_factor=avoidance_factor
            )

            if is_valid:
                logger.info(f"Iterative avoidance succeeded at iteration {iteration}")
                return best_route

            if violation_count >= best_violations:
                break  # Not improving
            best_violations = violation_count

            # Find the violated zone centers
            violated_zone_ids = {v["zone_id"] for v in violations}
            violated_zones = [z for z in risk_zones_data if z.get("id") in violated_zone_ids]

            if not violated_zones:
                break

            # Build focused exclude polygons for the violated zones
            focused_polygons = []
            total_circ = 0.0
            for zone in violated_zones:
                radius = zone["radius_meters"] * avoidance_factor * 3.0
                circ = 2 * math.pi * radius
                if total_circ + circ > 9500:
                    break
                polygon = risk_zone_service.create_circular_polygon(
                    zone["lon"], zone["lat"], radius, num_points=8
                )
                focused_polygons.append(polygon)
                total_circ += circ

            # Generate avoidance waypoints using route-local perpendicular directions
            coords = best_route.geometry.coordinates
            avoidance_waypoints = []
            for zone in violated_zones:
                z_lat, z_lon = zone["lat"], zone["lon"]
                z_radius = zone.get("radius_meters", 150)

                # Find nearest route point to this zone
                min_dist = float('inf')
                nearest_idx = 0
                for idx, coord in enumerate(coords):
                    dist = self._simple_distance(z_lat, z_lon, coord[1], coord[0])
                    if dist < min_dist:
                        min_dist = dist
                        nearest_idx = idx

                # Get route direction at nearest point for local perpendicular
                if nearest_idx > 0 and nearest_idx < len(coords) - 1:
                    route_dir_lat = coords[nearest_idx + 1][1] - coords[nearest_idx - 1][1]
                    route_dir_lon = coords[nearest_idx + 1][0] - coords[nearest_idx - 1][0]
                elif nearest_idx > 0:
                    route_dir_lat = coords[nearest_idx][1] - coords[nearest_idx - 1][1]
                    route_dir_lon = coords[nearest_idx][0] - coords[nearest_idx - 1][0]
                else:
                    route_dir_lat = coords[min(1, len(coords) - 1)][1] - coords[0][1]
                    route_dir_lon = coords[min(1, len(coords) - 1)][0] - coords[0][0]

                rmag = math.sqrt(route_dir_lat**2 + route_dir_lon**2)
                if rmag > 0:
                    perp_lat = -route_dir_lon / rmag
                    perp_lon = route_dir_lat / rmag
                else:
                    perp_lat, perp_lon = 0.0, 1.0

                offset_deg = (z_radius * (2.5 + iteration * 1.0)) / 111000
                wp1 = (z_lat + perp_lat * offset_deg, z_lon + perp_lon * offset_deg)
                wp2 = (z_lat - perp_lat * offset_deg, z_lon - perp_lon * offset_deg)
                wp1_score = self._score_waypoint(wp1, risk_zones_data)
                wp2_score = self._score_waypoint(wp2, risk_zones_data)
                avoidance_waypoints.append(wp1 if wp1_score > wp2_score else wp2)

            # Try routing with waypoints + focused exclude polygons
            try:
                wp_request = self._build_multi_waypoint_request(
                    request, avoidance_waypoints,
                    exclude_polygons=focused_polygons if focused_polygons else None,
                )
                response = await self.client.post(
                    f"{self.valhalla_url}/route", json=wp_request
                )
                if not response.is_success:
                    continue

                route = await self._parse_valhalla_response(response.json(), request)
                if route.geometry.coordinates:
                    is_valid_new, new_violations, _ = risk_zone_service.validate_route_against_zones(
                        route.geometry.coordinates, all_zones, min_severity,
                        radius_factor=avoidance_factor,
                    )
                    if is_valid_new:
                        logger.info(f"Iterative avoidance found clean route at iteration {iteration}")
                        return route
                    if new_violations < best_violations:
                        best_route = route
                        best_violations = new_violations
            except Exception:
                continue

        return None

    async def _try_waypoint_avoidance(
        self, request: RouteRequest, risk_zones_data: list,
        all_zones: list, min_severity: str
    ) -> Optional[RouteResponse]:
        """Try routing with intermediate waypoints that avoid risk zones.

        Multi-stage approach:
        1. Single waypoint avoidance around zone clusters
        2. Multi-waypoint chains for routes through dense zone areas
        3. Extreme offset waypoints as last resort
        """

        origin = (request.origin.latitude, request.origin.longitude)
        dest = (request.destination.latitude, request.destination.longitude)

        zones_on_path = self._find_zones_on_path(origin, dest, risk_zones_data)
        if not zones_on_path:
            return None

        avg_lat = sum(z["lat"] for z in zones_on_path) / len(zones_on_path)
        avg_lon = sum(z["lon"] for z in zones_on_path) / len(zones_on_path)

        # Build focused exclude polygons for zones on path
        avoidance_factor = 0.25 if min_severity == "LOW" else 0.2
        path_exclude_polygons = []
        total_circ = 0.0
        for zone in zones_on_path:
            radius = zone["radius_meters"] * avoidance_factor * 3.0
            circ = 2 * math.pi * radius
            if total_circ + circ > 9500:
                break
            polygon = risk_zone_service.create_circular_polygon(
                zone["lon"], zone["lat"], radius, num_points=8
            )
            path_exclude_polygons.append(polygon)
            total_circ += circ

        # Calculate max zone radius on path for offset sizing
        max_zone_radius = max(z.get("radius_meters", 150) for z in zones_on_path)
        # Convert to degrees for offset calculation
        base_offset = (max_zone_radius * 2) / 111000

        # Stage 1: Single waypoint with increasing offsets
        waypoints = self._generate_avoidance_waypoints(
            origin, dest, avg_lat, avg_lon, risk_zones_data
        )

        # Add extra-wide offsets proportional to zone sizes
        dir_lat = dest[0] - origin[0]
        dir_lon = dest[1] - origin[1]
        mag = math.sqrt(dir_lat ** 2 + dir_lon ** 2)
        if mag > 0:
            perp_lat, perp_lon = -dir_lon / mag, dir_lat / mag
        else:
            perp_lat, perp_lon = 0.0, 1.0

        for mult in [2.0, 3.0, 4.0, 5.0]:
            offset = base_offset * mult
            wp1 = (avg_lat + perp_lat * offset, avg_lon + perp_lon * offset)
            wp2 = (avg_lat - perp_lat * offset, avg_lon - perp_lon * offset)
            wp1_score = self._score_waypoint(wp1, risk_zones_data)
            wp2_score = self._score_waypoint(wp2, risk_zones_data)
            waypoints.append(wp1 if wp1_score > wp2_score else wp2)

        best_route = None
        best_passes = float('inf')

        for wp in waypoints[:16]:
            try:
                wp_request = self._build_waypoint_request(
                    request, wp,
                    exclude_polygons=path_exclude_polygons if path_exclude_polygons else None,
                )
                response = await self.client.post(
                    f"{self.valhalla_url}/route", json=wp_request
                )
                if not response.is_success:
                    continue

                route = await self._parse_valhalla_response(response.json(), request)
                if not route.geometry.coordinates:
                    continue

                avoidance_factor = 0.25 if min_severity == "LOW" else 0.2
                is_valid, violation_count, _ = risk_zone_service.validate_route_against_zones(
                    route.geometry.coordinates, all_zones, min_severity,
                    radius_factor=avoidance_factor,
                )

                if is_valid:
                    logger.info(f"Found clean waypoint route via ({wp[0]:.5f}, {wp[1]:.5f})")
                    return route

                if violation_count < best_passes:
                    best_passes = violation_count
                    best_route = route

            except Exception:
                continue

        # Stage 2: Multi-waypoint chains - go around each individual zone
        if best_passes > 0 and len(zones_on_path) <= 5:
            for attempt in range(4):
                chain_waypoints = []
                multiplier = 2.0 + attempt * 1.5
                for zone in zones_on_path:
                    z_lat, z_lon = zone["lat"], zone["lon"]
                    z_radius = zone.get("radius_meters", 150)
                    offset_deg = (z_radius * multiplier) / 111000

                    wp1 = (z_lat + perp_lat * offset_deg, z_lon + perp_lon * offset_deg)
                    wp2 = (z_lat - perp_lat * offset_deg, z_lon - perp_lon * offset_deg)
                    wp1_score = self._score_waypoint(wp1, risk_zones_data)
                    wp2_score = self._score_waypoint(wp2, risk_zones_data)
                    chain_waypoints.append(wp1 if wp1_score > wp2_score else wp2)

                try:
                    chain_request = self._build_multi_waypoint_request(
                        request, chain_waypoints,
                        exclude_polygons=path_exclude_polygons if path_exclude_polygons else None,
                    )
                    response = await self.client.post(
                        f"{self.valhalla_url}/route", json=chain_request
                    )
                    if not response.is_success:
                        continue

                    route = await self._parse_valhalla_response(response.json(), request)
                    if not route.geometry.coordinates:
                        continue

                    avoidance_factor = 0.25 if min_severity == "LOW" else 0.2
                    is_valid, violation_count, _ = risk_zone_service.validate_route_against_zones(
                        route.geometry.coordinates, all_zones, min_severity,
                        radius_factor=avoidance_factor,
                    )

                    if is_valid:
                        logger.info(f"Found clean multi-waypoint route (attempt {attempt})")
                        return route

                    if violation_count < best_passes:
                        best_passes = violation_count
                        best_route = route

                except Exception:
                    continue

        # Only return fallback if BALANCED (where 1 low-severity pass may be acceptable)
        # For SAFEST, return None to force the engine to use the least-bad candidate
        if min_severity == "HIGH" and best_route and best_passes <= 1:
            return best_route
        return None

    def _build_multi_waypoint_request(
        self, request: RouteRequest, waypoints: List[Tuple[float, float]],
        exclude_polygons: Optional[List] = None,
    ) -> dict:
        """Build Valhalla request with multiple intermediate waypoints."""
        locations = [
            {"lat": request.origin.latitude, "lon": request.origin.longitude, "type": "break"},
        ]
        for wp in waypoints:
            locations.append({"lat": wp[0], "lon": wp[1], "type": "through"})
        locations.append(
            {"lat": request.destination.latitude, "lon": request.destination.longitude, "type": "break"}
        )
        result = {
            "locations": locations,
            "costing": "bicycle",
            "costing_options": {
                "bicycle": {
                    "bicycle_type": "Hybrid",
                    "use_roads": 0.3,
                    "use_hills": 0.3,
                    "avoid_bad_surfaces": 0.6,
                }
            },
            "directions_options": {"units": "meters", "language": "en-US"},
            "elevation_interval": 30,
            "format": "json",
        }
        if exclude_polygons:
            result["exclude_polygons"] = exclude_polygons
        return result

    async def _calculate_fastest_route(self, request: RouteRequest) -> RouteResponse:
        """Calculate the fastest route by trying multiple candidates.

        Tries different costing options and picks the one with lowest duration.
        """
        logger.info("Calculating FASTEST route")

        # Try multiple costing options to find the fastest
        route_options = [
            # Standard road routing - often fastest
            {"bicycle_type": "Road", "use_roads": 0.5, "use_hills": 0.3, "avoid_bad_surfaces": 0.5},
            # Cross bike - flexible, can be fast
            {"bicycle_type": "Cross", "use_roads": 0.6, "use_hills": 0.5, "avoid_bad_surfaces": 0.4},
            # Full road usage
            {"bicycle_type": "Road", "use_roads": 0.8, "use_hills": 0.6, "avoid_bad_surfaces": 0.3},
            # Hybrid - balanced approach
            {"bicycle_type": "Hybrid", "use_roads": 0.5, "use_hills": 0.4, "avoid_bad_surfaces": 0.5},
        ]

        best_route = None
        best_duration = float('inf')

        for i, options in enumerate(route_options):
            try:
                valhalla_request = self._build_base_valhalla_request(request, options)

                response = await self.client.post(
                    f"{self.valhalla_url}/route",
                    json=valhalla_request,
                )
                response.raise_for_status()
                valhalla_response = response.json()

                route = await self._parse_valhalla_response(valhalla_response, request)

                if route.summary.duration_seconds < best_duration:
                    best_duration = route.summary.duration_seconds
                    best_route = route
                    logger.debug(f"FASTEST candidate {i}: {best_duration}s")

            except Exception as e:
                logger.debug(f"FASTEST candidate {i} failed: {e}")
                continue

        # Also try with alternates to find potentially faster routes
        try:
            alt_request = self._build_base_valhalla_request(request, route_options[0])
            alt_request["alternates"] = 2

            response = await self.client.post(
                f"{self.valhalla_url}/route",
                json=alt_request,
            )
            response.raise_for_status()
            valhalla_response = response.json()

            # Check main route
            route = await self._parse_valhalla_response(valhalla_response, request)
            if route.summary.duration_seconds < best_duration:
                best_duration = route.summary.duration_seconds
                best_route = route

            # Check alternates
            for alt in valhalla_response.get("alternates", []):
                try:
                    alt_route = await self._parse_valhalla_response(alt, request)
                    if alt_route.summary.duration_seconds < best_duration:
                        best_duration = alt_route.summary.duration_seconds
                        best_route = alt_route
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"FASTEST alternates failed: {e}")

        if best_route:
            logger.info(f"Selected FASTEST route: {best_duration}s, {best_route.summary.distance_meters}m")
            return best_route

        # Fallback to basic route
        return await self._calculate_basic_safest(request)

    def _find_zones_on_path(
        self, origin: Tuple[float, float], dest: Tuple[float, float],
        zones: List[Dict]
    ) -> List[Dict]:
        """Find risk zones that are between origin and destination."""
        on_path = []
        o_lat, o_lon = origin
        d_lat, d_lon = dest

        # Bounding box with buffer
        min_lat = min(o_lat, d_lat) - 0.01
        max_lat = max(o_lat, d_lat) + 0.01
        min_lon = min(o_lon, d_lon) - 0.01
        max_lon = max(o_lon, d_lon) + 0.01

        for zone in zones:
            z_lat, z_lon = zone["lat"], zone["lon"]

            # Check if zone is within bounding box
            if not (min_lat <= z_lat <= max_lat and min_lon <= z_lon <= max_lon):
                continue

            # Check if zone is roughly on the path
            # Using simplified perpendicular distance
            d_oz = self._simple_distance(o_lat, o_lon, z_lat, z_lon)
            d_zd = self._simple_distance(z_lat, z_lon, d_lat, d_lon)
            d_od = self._simple_distance(o_lat, o_lon, d_lat, d_lon)

            if d_od > 0:
                detour = (d_oz + d_zd) / d_od
                if detour < 1.5:  # Zone is roughly on path
                    on_path.append(zone)

        return on_path

    def _simple_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Simple Euclidean distance for comparison (not actual meters)."""
        return math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)

    def _generate_avoidance_waypoints(
        self, origin: Tuple[float, float], dest: Tuple[float, float],
        cluster_lat: float, cluster_lon: float, all_zones: List[Dict]
    ) -> List[Tuple[float, float]]:
        """Generate waypoints that route around the risk zone cluster."""

        o_lat, o_lon = origin
        d_lat, d_lon = dest

        # Direction from origin to destination
        dir_lat = d_lat - o_lat
        dir_lon = d_lon - o_lon

        # Perpendicular directions (to go around the cluster)
        perp1_lat, perp1_lon = -dir_lon, dir_lat  # Rotate 90 degrees
        perp2_lat, perp2_lon = dir_lon, -dir_lat  # Rotate -90 degrees

        # Normalize
        mag = math.sqrt(perp1_lat**2 + perp1_lon**2)
        if mag > 0:
            perp1_lat /= mag
            perp1_lon /= mag
            perp2_lat /= mag
            perp2_lon /= mag

        waypoints = []

        # Generate waypoints at different distances from the cluster center
        for offset in [0.01, 0.02, 0.03, 0.04]:
            wp1 = (cluster_lat + perp1_lat * offset, cluster_lon + perp1_lon * offset)
            wp2 = (cluster_lat + perp2_lat * offset, cluster_lon + perp2_lon * offset)

            # Score each waypoint by minimum distance to any risk zone
            wp1_score = self._score_waypoint(wp1, all_zones)
            wp2_score = self._score_waypoint(wp2, all_zones)

            # Add both waypoints, best one first
            if wp1_score > wp2_score:
                waypoints.append(wp1)
                waypoints.append(wp2)
            else:
                waypoints.append(wp2)
                waypoints.append(wp1)

        # Also add waypoints at the midpoint offset perpendicular
        mid_lat = (o_lat + d_lat) / 2
        mid_lon = (o_lon + d_lon) / 2
        for offset in [0.015, 0.03]:
            wp1 = (mid_lat + perp1_lat * offset, mid_lon + perp1_lon * offset)
            wp2 = (mid_lat + perp2_lat * offset, mid_lon + perp2_lon * offset)
            wp1_score = self._score_waypoint(wp1, all_zones)
            wp2_score = self._score_waypoint(wp2, all_zones)
            if wp1_score > wp2_score:
                waypoints.append(wp1)
            else:
                waypoints.append(wp2)

        # Add extreme avoidance waypoints for routes deep in risk zones
        for offset in [0.05, 0.06]:
            wp1 = (cluster_lat + perp1_lat * offset, cluster_lon + perp1_lon * offset)
            wp2 = (cluster_lat + perp2_lat * offset, cluster_lon + perp2_lon * offset)
            wp1_score = self._score_waypoint(wp1, all_zones)
            wp2_score = self._score_waypoint(wp2, all_zones)
            waypoints.append(wp1 if wp1_score > wp2_score else wp2)

        return waypoints[:12]  # More waypoint options

    def _score_waypoint(self, waypoint: Tuple[float, float], zones: List[Dict]) -> float:
        """Score a waypoint - higher is better (farther from risk zones)."""
        if not zones:
            return 1.0

        min_dist = min(
            self._simple_distance(waypoint[0], waypoint[1], z["lat"], z["lon"])
            for z in zones
        )
        return min_dist

    def _build_waypoint_request(
        self, request: RouteRequest, waypoint: Tuple[float, float],
        exclude_polygons: Optional[List] = None,
    ) -> dict:
        """Build Valhalla request with an intermediate waypoint."""
        result = {
            "locations": [
                {
                    "lat": request.origin.latitude,
                    "lon": request.origin.longitude,
                    "type": "break",
                },
                {
                    "lat": waypoint[0],
                    "lon": waypoint[1],
                    "type": "through",  # Pass through, don't stop
                },
                {
                    "lat": request.destination.latitude,
                    "lon": request.destination.longitude,
                    "type": "break",
                },
            ],
            "costing": "bicycle",
            "costing_options": {
                "bicycle": {
                    "bicycle_type": "Hybrid",
                    "use_roads": 0.2,
                    "use_hills": 0.3,
                    "avoid_bad_surfaces": 0.7,
                }
            },
            "directions_options": {"units": "meters", "language": "en-US"},
            "elevation_interval": 30,
            "format": "json",
        }
        if exclude_polygons:
            result["exclude_polygons"] = exclude_polygons
        return result

    async def _calculate_basic_safest(self, request: RouteRequest) -> RouteResponse:
        """Calculate a basic safest route without risk zone consideration.

        Uses normal road routing - does not force bike lanes.
        """
        options = {
            "bicycle_type": "Road",
            "use_roads": 0.5,  # Allow normal roads
            "use_hills": 0.3,  # Prefer gentler hills
            "avoid_bad_surfaces": 0.6,  # Prefer good surfaces
            "shortest": False,
        }
        valhalla_request = self._build_base_valhalla_request(request, options)
        response = await self.client.post(
            f"{self.valhalla_url}/route",
            json=valhalla_request,
        )
        response.raise_for_status()
        return await self._parse_valhalla_response(response.json(), request)

    def _build_base_valhalla_request(
        self, request: RouteRequest, costing_options: dict
    ) -> dict:
        """Build a basic Valhalla request with custom costing options."""
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
            "costing": "bicycle",
            "costing_options": {"bicycle": costing_options},
            "directions_options": {
                "units": "meters",
                "language": "en-US",
            },
            "elevation_interval": 30,
            "format": "json",
        }

    async def calculate_alternatives(
        self,
        request: RouteRequest,
        num_alternatives: int = 3,
    ) -> List[RouteResponse]:
        """Calculate multiple alternative routes.

        Returns routes in order: BALANCED, SAFEST, FASTEST
        Ensures FASTEST always has the lowest duration.
        """

        routes = []

        # Calculate routes with different profiles
        # Order: BALANCED, SAFEST, FASTEST (matching UI order)
        profiles = [RouteProfile.BALANCED, RouteProfile.SAFEST, RouteProfile.FASTEST]

        for profile in profiles[:num_alternatives]:
            modified_request = request.model_copy()
            modified_request.preferences.profile = profile

            try:
                route = await self.calculate_route(modified_request)
                routes.append(route)
            except ValueError:
                continue

        # Ensure FASTEST is actually the fastest (lowest duration)
        # If another route is faster, swap them
        if len(routes) >= 3:
            fastest_idx = 2  # FASTEST position
            fastest_route = routes[fastest_idx]

            for i in range(len(routes)):
                if i != fastest_idx and routes[i].summary.duration_seconds < fastest_route.summary.duration_seconds:
                    # Another route is faster, use it for FASTEST
                    # This shouldn't happen often, but ensures consistency
                    routes[fastest_idx], routes[i] = routes[i], routes[fastest_idx]
                    fastest_route = routes[fastest_idx]

        return routes

    async def _get_accurate_bike_lane_percentage(
        self, coordinates: List[List[float]]
    ) -> Tuple[float, Dict[str, float]]:
        """Get accurate bike lane percentage using Valhalla's trace_attributes endpoint.

        This uses map matching to get actual edge attributes including cycle_lane data.

        Args:
            coordinates: List of [lon, lat] coordinates from the route geometry

        Returns:
            Tuple of (bike_lane_percentage, edge_stats_dict)
        """
        if not coordinates or len(coordinates) < 2:
            return 0.0, {}

        # Sample coordinates to avoid overwhelming the API (max ~100 points)
        if len(coordinates) > 100:
            step = len(coordinates) // 100
            sampled_coords = coordinates[::step]
            # Always include the last point
            if sampled_coords[-1] != coordinates[-1]:
                sampled_coords.append(coordinates[-1])
        else:
            sampled_coords = coordinates

        # Build shape for trace_attributes (lat, lon format for Valhalla)
        shape = [{"lat": coord[1], "lon": coord[0]} for coord in sampled_coords]

        trace_request = {
            "shape": shape,
            "costing": "bicycle",
            "shape_match": "map_snap",
            "filters": {
                "attributes": [
                    "edge.cycle_lane",
                    "edge.length",
                    "edge.use",
                    "edge.road_class",
                    "edge.surface",
                ],
                "action": "include",
            },
        }

        try:
            response = await self.client.post(
                f"{self.valhalla_url}/trace_attributes",
                json=trace_request,
            )
            response.raise_for_status()
            trace_data = response.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.warning(f"Failed to get trace_attributes: {e}")
            return 0.0, {}

        # Calculate bike lane percentage from edge data
        edges = trace_data.get("edges", [])
        if not edges:
            return 0.0, {}

        total_distance = 0.0
        bike_lane_distance = 0.0
        protected_distance = 0.0
        dedicated_distance = 0.0
        shared_distance = 0.0
        road_distance = 0.0

        for edge in edges:
            length_km = edge.get("length", 0)
            length_m = length_km * 1000  # Convert to meters
            total_distance += length_m

            cycle_lane = edge.get("cycle_lane", "none")
            use = edge.get("use", "road")

            # Categorize by cycle lane type
            # Valhalla cycle_lane values: "none", "shared", "dedicated", "separated"
            if cycle_lane == "separated":
                # Protected/separated bike lane - best infrastructure
                bike_lane_distance += length_m
                protected_distance += length_m
            elif cycle_lane == "dedicated":
                # Dedicated bike lane (painted, not physically separated)
                bike_lane_distance += length_m
                dedicated_distance += length_m
            elif cycle_lane == "shared":
                # Shared lane markings (sharrows)
                bike_lane_distance += length_m
                shared_distance += length_m
            elif use in ["cycleway", "path", "footway", "pedestrian"]:
                # Off-street paths, cycleways, etc. (count as bike infrastructure)
                bike_lane_distance += length_m
                protected_distance += length_m
            else:
                # Regular road without bike infrastructure
                road_distance += length_m

        if total_distance == 0:
            return 0.0, {}

        bike_lane_percentage = (bike_lane_distance / total_distance) * 100

        edge_stats = {
            "total_distance_m": total_distance,
            "bike_lane_distance_m": bike_lane_distance,
            "protected_distance_m": protected_distance,
            "dedicated_distance_m": dedicated_distance,
            "shared_distance_m": shared_distance,
            "road_distance_m": road_distance,
        }

        logger.info(
            f"Bike lane stats: {bike_lane_percentage:.1f}% bike lanes "
            f"({protected_distance:.0f}m protected, {dedicated_distance:.0f}m dedicated, "
            f"{shared_distance:.0f}m shared, {road_distance:.0f}m road)"
        )

        return bike_lane_percentage, edge_stats

    async def _build_valhalla_request(self, request: RouteRequest) -> dict:
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

        valhalla_request = {
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
            "elevation_interval": 30,  # Request elevation data every 30 meters
            "format": "json",
        }

        return valhalla_request

    def _build_costing_options(
        self, preferences: RoutePreferences, vehicle_type: VehicleType
    ) -> dict:
        """Build Valhalla costing options from preferences.

        Profile behaviors:
        - SAFEST: Normal routing but avoids risk zones (handled in _calculate_safest_route)
        - BALANCED: Mix roads/bike lanes for efficiency
        - FASTEST: Pure time optimization

        The "Bike Lane Only" toggle (prefer_bike_lanes) is the ONLY way to force bike lanes.
        """

        options = {
            "bicycle_type": "Road" if vehicle_type == VehicleType.BIKE else "Hybrid",
            "use_roads": 0.5,  # Balance between roads and bike paths
            "use_hills": 0.5 if not preferences.avoid_hills else 0.1,
            "avoid_bad_surfaces": 0.5,
        }

        # Adjust based on profile
        if preferences.profile == RouteProfile.SAFEST:
            # Safest: Normal routing - risk zone avoidance is handled separately
            # Does NOT force bike lanes (user must toggle "Bike Lane Only" for that)
            options["use_roads"] = 0.5  # Allow normal roads
            options["use_hills"] = 0.3  # Prefer gentler hills
            options["avoid_bad_surfaces"] = 0.6  # Prefer good surfaces
            options["shortest"] = False
        elif preferences.profile == RouteProfile.FASTEST:
            # Fastest: Pure time optimization, use roads freely
            # NOTE: Valhalla's "shortest" means shortest DISTANCE, not time
            # To get fastest time, we remove shortest and let Valhalla optimize for time
            options["use_roads"] = 1.0  # Use roads freely for fastest route
            options["use_hills"] = 1.0  # Accept any hills (going downhill is faster)
            options["avoid_bad_surfaces"] = 0.0  # Don't avoid surfaces
            # Don't set "shortest" - Valhalla optimizes for time by default
        elif preferences.profile == RouteProfile.BALANCED:
            # Balanced: Mix roads and bike lanes intelligently
            options["use_roads"] = 0.5  # Balance road and bike lane usage
            options["use_hills"] = 0.5 if not preferences.avoid_hills else 0.2
            options["avoid_bad_surfaces"] = 0.5
            options["shortest"] = False
        elif preferences.profile == RouteProfile.SCENIC:
            options["use_roads"] = 0.3
            options["use_hills"] = 0.4
            options["avoid_bad_surfaces"] = 0.6

        # Handle "Bike Lane Only" toggle - when enabled, ONLY use bike lanes
        # This is the ONLY way to force bike-lane-only routing
        if preferences.prefer_bike_lanes:
            # Force bike lanes only - set use_roads to minimum
            options["use_roads"] = 0.0  # Force bike lanes/cycleways only
            options["avoid_bad_surfaces"] = 0.8

        # Override with avoid_hills if explicitly set
        if preferences.avoid_hills:
            options["use_hills"] = 0.1

        return options

    async def _parse_valhalla_response(
        self, response: dict, request: RouteRequest
    ) -> RouteResponse:
        """Parse Valhalla response into our format."""

        trip = response.get("trip", {})
        legs = trip.get("legs", [])

        if not legs:
            raise ValueError("No route found")

        # Extract summary
        summary = trip.get("summary", {})

        # Build geometry from legs and collect elevation data
        all_coordinates = []
        all_elevations = []
        parsed_legs = []
        total_bike_lane_distance = 0
        total_distance = 0

        for leg in legs:
            shape = leg.get("shape", "")
            leg_coords = self._decode_polyline(shape)
            all_coordinates.extend(leg_coords)

            # Collect elevation data
            elevations = leg.get("elevation", [])
            all_elevations.extend(elevations)
            elevation_interval = leg.get("elevation_interval", 30)

            # Parse maneuvers and estimate bike lane usage
            maneuvers = []
            for m in leg.get("maneuvers", []):
                maneuver = self._parse_maneuver(m)
                maneuvers.append(maneuver)

                # Estimate bike lane usage from travel_type
                # Valhalla travel_type for bicycle: "road", "cycleway", "path", etc.
                travel_type = m.get("travel_type", "")
                segment_distance = m.get("length", 0) * 1000  # km to m
                total_distance += segment_distance

                # Count as bike lane if it's a cycleway, path, or bike-friendly
                if travel_type in ["cycleway", "path", "footway", "pedestrian"]:
                    total_bike_lane_distance += segment_distance

            leg_summary = leg.get("summary", {})
            leg_distance_m = int(leg_summary.get("length", 0) * 1000)
            # Use Valhalla's actual travel time which accounts for road class, elevation, turns
            leg_duration_s = int(leg_summary.get("time", 0))
            parsed_legs.append(
                RouteLeg(
                    geometry=GeoJSONLineString(coordinates=leg_coords),
                    distance_meters=leg_distance_m,
                    duration_seconds=leg_duration_s,
                    maneuvers=maneuvers,
                )
            )

        # Calculate elevation statistics
        elevation_gain, elevation_loss, max_grade = self._calculate_elevation_stats(
            all_elevations, elevation_interval if legs else 30
        )

        # Calculate accurate bike lane percentage using SF Open Data bike lanes
        # This uses the same data source as the frontend bike lane layer
        route_distance = summary.get("length", 0) * 1000  # km to m

        # Get accurate bike lane percentage by intersecting with SF bike lane data
        bike_lane_percentage, bike_stats = await bike_lane_service.calculate_bike_lane_percentage(
            all_coordinates
        )

        # If SF data unavailable, fall back to Valhalla trace_attributes
        if bike_lane_percentage == 0 and route_distance > 0:
            fallback_percentage, _ = await self._get_accurate_bike_lane_percentage(
                all_coordinates
            )
            if fallback_percentage > 0:
                bike_lane_percentage = fallback_percentage
                logger.info(f"Using Valhalla fallback for bike lane %: {bike_lane_percentage:.1f}%")

        # Calculate risk analysis based on route proximity to risk zones
        risk_score = 0.0
        zone_passes = 0
        zones_passed = []
        risk_zones_data = []
        try:
            risk_zones_data = await risk_zone_service.get_risk_zones()
            if risk_zones_data and all_coordinates:
                risk_score, zone_passes, zones_passed = risk_zone_service.calculate_route_risk_score(
                    all_coordinates, risk_zones_data
                )
                logger.info(f"Route risk analysis: score={risk_score:.2f}, zone_passes={zone_passes}")
        except RiskZoneServiceError:
            # Re-raise critical risk zone failures - don't silently degrade safety
            raise
        except Exception as e:
            # Non-critical failures (e.g., calculation errors) can be logged and continued
            logger.warning(f"Failed to calculate route risk: {e}")

        # Use Valhalla's actual travel time from trip summary
        # This accounts for road class, elevation, turns, surface type, and bicycle costing
        # Valhalla returns time in seconds
        valhalla_duration = int(summary.get("time", 0))

        # Fallback to calculated duration only if Valhalla didn't provide time
        if valhalla_duration == 0 and route_distance > 0:
            # Average urban cycling speed: ~15 km/h = 4.17 m/s
            valhalla_duration = int(route_distance / 4.17)
            logger.warning(f"Valhalla time missing, using fallback: {valhalla_duration}s for {route_distance}m")
        else:
            # Log the actual Valhalla timing for debugging
            avg_speed_kmh = (route_distance / 1000) / (valhalla_duration / 3600) if valhalla_duration > 0 else 0
            logger.debug(
                f"Valhalla route timing: {valhalla_duration}s for {route_distance:.0f}m "
                f"(avg {avg_speed_kmh:.1f} km/h)"
            )

        # Calculate route summary
        route_summary = RouteSummary(
            distance_meters=int(route_distance),
            duration_seconds=valhalla_duration,
            elevation_gain_meters=int(elevation_gain),
            elevation_loss_meters=int(elevation_loss),
            max_grade_percent=round(max_grade, 1),
            bike_lane_percentage=round(bike_lane_percentage, 1),
            risk_score=round(risk_score, 2),
        )

        # Build risk analysis
        high_severity_count = sum(
            1 for zid in zones_passed
            for z in risk_zones_data if z.get("id") == zid and z.get("severity") in ("HIGH", "CRITICAL")
        ) if zones_passed else 0

        # Convert zone IDs to UUIDs (filter out any invalid ones)
        valid_zone_uuids = []
        for zid in zones_passed[:10]:
            try:
                valid_zone_uuids.append(uuid.UUID(str(zid)))
            except (ValueError, TypeError):
                continue

        return RouteResponse(
            route_id=uuid.uuid4(),
            geometry=GeoJSONLineString(coordinates=all_coordinates),
            summary=route_summary,
            legs=parsed_legs,
            risk_analysis=RouteRiskAnalysis(
                total_risk_zones=zone_passes,
                high_severity_zones=high_severity_count,
                risk_zone_ids=valid_zone_uuids,
            ),
            warnings=[],
        )

    def _calculate_elevation_stats(
        self, elevations: List[float], interval: float
    ) -> Tuple[float, float, float]:
        """Calculate elevation gain, loss, and max grade from elevation data.

        Args:
            elevations: List of elevation values in meters
            interval: Distance between elevation points in meters

        Returns:
            Tuple of (elevation_gain, elevation_loss, max_grade_percent)
        """
        if not elevations or len(elevations) < 2:
            return 0, 0, 0

        elevation_gain = 0
        elevation_loss = 0
        max_grade = 0

        for i in range(1, len(elevations)):
            diff = elevations[i] - elevations[i - 1]

            if diff > 0:
                elevation_gain += diff
            else:
                elevation_loss += abs(diff)

            # Calculate grade as percentage (rise/run * 100)
            if interval > 0:
                grade = abs(diff) / interval * 100
                max_grade = max(max_grade, grade)

        return elevation_gain, elevation_loss, max_grade

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

    def _generate_mock_route(self, request: RouteRequest) -> RouteResponse:
        """Generate a mock route for development testing when Valhalla is unavailable."""

        origin = request.origin
        dest = request.destination

        # Calculate straight-line distance (Haversine formula)
        R = 6371000  # Earth radius in meters
        lat1, lon1 = math.radians(origin.latitude), math.radians(origin.longitude)
        lat2, lon2 = math.radians(dest.latitude), math.radians(dest.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c

        # Estimate duration (assuming ~15 km/h average for micromobility)
        duration = int(distance / (15 * 1000 / 3600))  # seconds

        # Generate intermediate points for a more realistic route line
        num_points = max(10, int(distance / 100))  # One point every ~100m
        coordinates = []
        for i in range(num_points + 1):
            t = i / num_points
            lat = origin.latitude + t * (dest.latitude - origin.latitude)
            lon = origin.longitude + t * (dest.longitude - origin.longitude)
            coordinates.append([lon, lat])

        # Create mock maneuvers
        maneuvers = [
            Maneuver(
                type=ManeuverType.DEPART,
                instruction="Start heading toward your destination",
                verbal_instruction="Start heading toward your destination",
                location=Coordinate(latitude=origin.latitude, longitude=origin.longitude),
                distance_meters=int(distance),
                street_name=None,
                bike_lane_status=BikeLaneStatus.NONE,
                alerts=[],
            ),
            Maneuver(
                type=ManeuverType.ARRIVE,
                instruction="You have arrived at your destination",
                verbal_instruction="You have arrived at your destination",
                location=Coordinate(latitude=dest.latitude, longitude=dest.longitude),
                distance_meters=0,
                street_name=None,
                bike_lane_status=BikeLaneStatus.NONE,
                alerts=[],
            ),
        ]

        leg = RouteLeg(
            geometry=GeoJSONLineString(coordinates=coordinates),
            distance_meters=int(distance),
            duration_seconds=duration,
            maneuvers=maneuvers,
        )

        summary = RouteSummary(
            distance_meters=int(distance),
            duration_seconds=duration,
            elevation_gain_meters=0,
            elevation_loss_meters=0,
            max_grade_percent=0,
            bike_lane_percentage=50,  # Mock value
            risk_score=0.3,  # Mock value
        )

        return RouteResponse(
            route_id=uuid.uuid4(),
            geometry=GeoJSONLineString(coordinates=coordinates),
            summary=summary,
            legs=[leg],
            risk_analysis=RouteRiskAnalysis(
                total_risk_zones=0,
                high_severity_zones=0,
                risk_zone_ids=[],
            ),
            warnings=[],
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
