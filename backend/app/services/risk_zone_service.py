"""Risk zone service for routing integration."""

import math
import logging
from typing import List, Tuple, Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from shapely import wkb

logger = logging.getLogger(__name__)


class RiskZoneServiceError(Exception):
    """Raised when risk zone data cannot be loaded."""
    pass


class RiskZoneService:
    """Service for fetching and processing risk zones for route avoidance."""

    def __init__(self):
        self._cached_zones: List[Dict[str, Any]] = []
        self._cache_loaded = False

    async def get_risk_zones(self, db: Optional[AsyncSession] = None) -> List[Dict[str, Any]]:
        """Fetch all active risk zones from the database.

        Returns list of zones with coordinates and radius.
        """
        if self._cache_loaded and self._cached_zones:
            return self._cached_zones

        # If no db session provided, try to get zones from cache or raise error
        if db is None:
            # Try importing and getting a new session
            try:
                from app.db.session import async_session_maker
                async with async_session_maker() as session:
                    return await self._fetch_zones_from_db(session)
            except Exception as e:
                logger.error(f"CRITICAL: Failed to load risk zones from DB: {e}")
                # Return cached data if available, but log prominently
                if self._cached_zones:
                    logger.warning("Using stale cached risk zones due to DB failure")
                    return self._cached_zones
                # No cache available - this is a safety degradation
                raise RiskZoneServiceError(f"Risk zone data unavailable: {e}")

        return await self._fetch_zones_from_db(db)

    async def _fetch_zones_from_db(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Fetch risk zones directly from the database."""
        try:
            from app.models.risk_zone import RiskZone

            query = select(RiskZone).where(RiskZone.is_active == True)
            result = await db.execute(query)
            zones = result.scalars().all()

            self._cached_zones = []
            for zone in zones:
                try:
                    # Parse WKB geometry to get coordinates
                    geom = wkb.loads(bytes(zone.geometry.data))
                    if geom.geom_type == "Point":
                        lon, lat = geom.x, geom.y
                    else:
                        # For non-point geometries, use centroid
                        centroid = geom.centroid
                        lon, lat = centroid.x, centroid.y

                    self._cached_zones.append({
                        "id": str(zone.id),
                        "lon": lon,
                        "lat": lat,
                        "radius_meters": zone.alert_radius_meters or 100,
                        "severity": zone.severity.value.upper() if zone.severity else "MEDIUM",
                        "reported_count": zone.reported_count or 0,
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse zone {zone.id}: {e}")
                    continue

            self._cache_loaded = True
            logger.info(f"Loaded {len(self._cached_zones)} risk zones from database")
            return self._cached_zones

        except Exception as e:
            logger.error(f"CRITICAL: Failed to fetch risk zones from database: {e}")
            # Return cached data if available
            if self._cached_zones:
                logger.warning("Using stale cached risk zones due to DB failure")
                return self._cached_zones
            raise RiskZoneServiceError(f"Risk zone data unavailable: {e}")

    def create_circular_polygon(
        self, lon: float, lat: float, radius_meters: float, num_points: int = 16
    ) -> List[List[float]]:
        """Create a circular polygon approximation around a point.

        Args:
            lon: Center longitude
            lat: Center latitude
            radius_meters: Radius in meters
            num_points: Number of points to approximate circle

        Returns:
            List of [lon, lat] coordinates forming a closed polygon
        """
        # Convert radius to approximate degrees
        # At ~37.78 lat (SF), 1 degree lat ≈ 111km, 1 degree lon ≈ 88km
        lat_offset = radius_meters / 111000
        lon_offset = radius_meters / (111000 * math.cos(math.radians(lat)))

        coords = []
        for i in range(num_points):
            angle = (2 * math.pi * i) / num_points
            point_lon = lon + lon_offset * math.cos(angle)
            point_lat = lat + lat_offset * math.sin(angle)
            coords.append([point_lon, point_lat])

        # Close the polygon
        coords.append(coords[0])

        return coords

    async def get_exclude_polygons_for_safest(
        self,
        buffer_multiplier: float = 1.5,
        min_severity: str = "MEDIUM",
        max_total_circumference: float = 9500
    ) -> List[List[List[float]]]:
        """Get exclude polygons for Valhalla's safest routing.

        Uses compact polygons (capped radius) to fit as many zone centers as
        possible within Valhalla's circumference limit. Post-route validation
        checks against actual zone radii.

        Args:
            buffer_multiplier: Multiply capped radius by this factor
            min_severity: Minimum severity to include
            max_total_circumference: Maximum total circumference in meters

        Returns:
            List of polygon coordinate arrays for Valhalla exclude_polygons
        """
        zones = await self.get_risk_zones()

        if not zones:
            return []

        filtered_zones = self.filter_zones_by_severity(zones, min_severity)
        filtered_zones.sort(key=lambda z: z.get("reported_count", 0), reverse=True)

        exclude_polygons = []
        total_circumference = 0.0
        num_points = 8  # 8 points for better circle approximation (fixes gap at corners)

        # Use capped radius to fit more zones within Valhalla's circumference budget.
        # Post-route validation checks against the actual avoidance radius (0.5x alert_radius).
        for zone in filtered_zones:
            radius = min(zone["radius_meters"], 150) * buffer_multiplier
            circumference = 2 * math.pi * radius

            if total_circumference + circumference > max_total_circumference:
                logger.info(f"Stopping at {len(exclude_polygons)} polygons due to circumference limit")
                break

            polygon = self.create_circular_polygon(
                zone["lon"], zone["lat"], radius, num_points=num_points
            )
            exclude_polygons.append(polygon)
            total_circumference += circumference

        logger.info(
            f"Created {len(exclude_polygons)} exclude polygons for routing "
            f"(min_severity={min_severity}, total_circ={total_circumference:.0f}m)"
        )
        return exclude_polygons

    async def get_exclude_polygon_batches(
        self,
        buffer_multiplier: float = 1.5,
        min_severity: str = "LOW",
        max_total_circumference: float = 9500,
    ) -> List[List[List[List[float]]]]:
        """Get exclude polygons split into batches that each fit within Valhalla's limit.

        Uses compact radius (max 120m) to maximize zone coverage per batch.
        Post-route validation checks against actual zone radii.

        Returns:
            List of batches, where each batch is a list of polygon coordinate arrays
        """
        zones = await self.get_risk_zones()
        if not zones:
            return []

        filtered_zones = self.filter_zones_by_severity(zones, min_severity)
        filtered_zones.sort(key=lambda z: z.get("reported_count", 0), reverse=True)

        batches = []
        current_batch = []
        current_circumference = 0.0
        num_points = 8

        for zone in filtered_zones:
            radius = min(zone["radius_meters"], 150) * buffer_multiplier
            circumference = 2 * math.pi * radius

            if current_circumference + circumference > max_total_circumference:
                if current_batch:
                    batches.append(current_batch)
                current_batch = []
                current_circumference = 0.0

            polygon = self.create_circular_polygon(
                zone["lon"], zone["lat"], radius, num_points=num_points
            )
            current_batch.append(polygon)
            current_circumference += circumference

        if current_batch:
            batches.append(current_batch)

        logger.info(f"Created {len(batches)} exclude polygon batches covering {len(filtered_zones)} zones")
        return batches

    def validate_route_against_zones(
        self,
        route_coords: List[List[float]],
        zones: List[Dict[str, Any]],
        min_severity: str = "LOW",
        radius_factor: float = 0.25,
    ) -> Tuple[bool, int, List[Dict[str, Any]]]:
        """Validate that a route does not pass through the core of forbidden zones.

        Uses a radius_factor to determine the avoidance zone:
        - 1.0 = full alert_radius (very strict, may be impossible in dense areas)
        - 0.5 = half alert_radius (avoids zone cores, practical for dense urban areas)
        - 0.3 = core only (minimum viable avoidance)

        The alert_radius_meters is the "alert when approaching" radius, which is
        larger than the actual high-danger core. For routing avoidance, we use a
        fraction of it to represent the true danger zone.

        Args:
            route_coords: List of [lon, lat] coordinates
            zones: All risk zones
            min_severity: Which zones to check against
            radius_factor: Fraction of alert_radius to use for avoidance check

        Returns:
            Tuple of (is_valid, violation_count, violations_detail)
        """
        filtered_zones = self.filter_zones_by_severity(zones, min_severity)
        violations = []

        for zone in filtered_zones:
            zone_lon, zone_lat = zone["lon"], zone["lat"]
            # Use reduced radius for routing avoidance
            avoidance_radius = zone["radius_meters"] * radius_factor

            for coord in route_coords:
                lon, lat = coord[0], coord[1]
                dist = self._haversine_distance(lat, lon, zone_lat, zone_lon)
                if dist < avoidance_radius:
                    violations.append({
                        "zone_id": zone.get("id"),
                        "reported_count": zone.get("reported_count", 0),
                        "distance_m": round(dist, 1),
                        "zone_radius_m": zone["radius_meters"],
                        "avoidance_radius_m": round(avoidance_radius, 1),
                    })
                    break

        is_valid = len(violations) == 0
        return is_valid, len(violations), violations

    def calculate_route_risk_score(
        self,
        route_coords: List[List[float]],
        zones: List[Dict[str, Any]],
        radius_factor: float = 0.25,
    ) -> Tuple[float, int, List[str]]:
        """Calculate a risk score for a route based on proximity to risk zone cores.

        Uses radius_factor to determine the danger zone radius (same as routing avoidance).

        Args:
            route_coords: List of [lon, lat] route coordinates
            zones: List of risk zone dicts with lon, lat, radius_meters, severity
            radius_factor: Fraction of alert_radius to use as danger zone

        Returns:
            Tuple of (risk_score 0-1, num_zone_passes, list of zone_ids passed)
        """
        if not route_coords or not zones:
            return 0.0, 0, []

        zone_passes = 0
        zones_passed = []
        total_risk_points = 0.0

        severity_weights = {
            "LOW": 0.25,
            "MEDIUM": 0.5,
            "HIGH": 1.0,
            "CRITICAL": 1.5,
        }

        for zone in zones:
            zone_lon, zone_lat = zone["lon"], zone["lat"]
            zone_radius = zone["radius_meters"] * radius_factor
            zone_severity = zone.get("severity", "MEDIUM")

            for coord in route_coords:
                lon, lat = coord[0], coord[1]
                dist = self._haversine_distance(lat, lon, zone_lat, zone_lon)

                if dist < zone_radius:
                    zone_passes += 1
                    zones_passed.append(zone.get("id", "unknown"))
                    closeness = 1 - (dist / zone_radius) if zone_radius > 0 else 1.0
                    weight = severity_weights.get(zone_severity, 0.5)
                    total_risk_points += closeness * weight
                    break

        if zones:
            risk_score = min(1.0, total_risk_points / (len(zones) * 0.3))
        else:
            risk_score = 0.0

        return risk_score, zone_passes, zones_passed

    def _haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance in meters between two points."""
        R = 6371000  # Earth radius in meters
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat/2)**2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def clear_cache(self):
        """Clear the cached risk zones."""
        self._cached_zones = []
        self._cache_loaded = False

    def filter_zones_by_severity(
        self,
        zones: List[Dict[str, Any]],
        min_severity: str = "LOW"
    ) -> List[Dict[str, Any]]:
        """Filter zones by minimum severity level.

        Uses reported_count for consistency with visual display:
        - "LOW": All zones (160+)
        - "MEDIUM": Yellow/Orange zones (160+)
        - "HIGH": Dark red zones only (200+ crashes)
        - "CRITICAL": Very high crash zones (250+ crashes)

        Args:
            zones: List of risk zone dicts
            min_severity: Minimum severity to include

        Returns:
            Filtered list of zones
        """
        # Map severity to minimum reported_count threshold
        # This matches the frontend color coding:
        # - 140-179: yellow (MEDIUM)
        # - 180-229: light red (HIGH)
        # - 230+: dark red (CRITICAL)
        severity_thresholds = {
            "LOW": 140,      # All visible zones
            "MEDIUM": 140,   # Yellow and above
            "HIGH": 180,     # Light red and above (skip yellow)
            "CRITICAL": 230, # Dark red only
        }

        min_count = severity_thresholds.get(min_severity.upper(), 160)

        filtered = [
            z for z in zones
            if z.get("reported_count", 0) >= min_count
        ]

        logger.debug(f"Filtered zones: {len(filtered)} of {len(zones)} with min_severity={min_severity} (min_count={min_count})")
        return filtered

    def calculate_route_risk_score_filtered(
        self,
        route_coords: List[List[float]],
        zones: List[Dict[str, Any]],
        min_severity: str = "LOW"
    ) -> Tuple[float, int, List[str]]:
        """Calculate risk score considering only zones above minimum severity.

        For BALANCED routing, only count HIGH and CRITICAL zones.
        For SAFEST routing, count all zones.

        Args:
            route_coords: List of [lon, lat] route coordinates
            zones: List of risk zone dicts
            min_severity: Minimum severity to count

        Returns:
            Tuple of (risk_score 0-1, num_zone_passes, list of zone_ids passed)
        """
        filtered_zones = self.filter_zones_by_severity(zones, min_severity)
        return self.calculate_route_risk_score(route_coords, filtered_zones)


# Singleton instance
risk_zone_service = RiskZoneService()
