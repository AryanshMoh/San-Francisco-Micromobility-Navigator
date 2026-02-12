"""Bike lane service - fetches and caches SF bike lane data for accurate calculations."""

import logging
import time
from typing import List, Tuple, Optional, Dict, Any

import httpx
from shapely.geometry import LineString, MultiLineString, shape
from shapely.ops import unary_union
from shapely import prepared

logger = logging.getLogger(__name__)

# SF Open Data - SFMTA Bikeway Network (same source as frontend)
SF_BIKE_LANES_API = "https://data.sfgov.org/resource/ygmz-vaxd.geojson?$limit=10000"

# Cache duration in seconds (1 hour)
CACHE_DURATION = 3600

# Facility types that count as REAL bike lanes (not just sharrows/bike routes)
# CLASS I: Off-street bike paths
# CLASS II: Painted bike lanes on streets
# CLASS IV: Protected/separated bike lanes
# Exclude CLASS III which are just "Bike Routes" (sharrows on regular roads)
REAL_BIKE_LANE_TYPES = {"CLASS I", "CLASS II", "CLASS IV"}


class BikeLaneService:
    """Service for calculating accurate bike lane percentage using SF Open Data."""

    def __init__(self):
        self._bike_lanes_cache: Optional[Dict[str, Any]] = None
        self._bike_lanes_geometry: Optional[Any] = None  # Unified geometry for intersection
        self._prepared_geometry: Optional[Any] = None  # Prepared geometry for fast checks
        self._cache_timestamp: float = 0
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _fetch_bike_lanes(self) -> Dict[str, Any]:
        """Fetch bike lane data from SF Open Data API."""
        try:
            response = await self._client.get(SF_BIKE_LANES_API)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch bike lanes from SF Open Data: {e}")
            return {"type": "FeatureCollection", "features": []}

    async def _ensure_cache(self) -> None:
        """Ensure bike lane data is cached and up to date."""
        current_time = time.time()

        if (
            self._bike_lanes_cache is None
            or current_time - self._cache_timestamp > CACHE_DURATION
        ):
            logger.info("Fetching SF bike lane data from Open Data API...")
            self._bike_lanes_cache = await self._fetch_bike_lanes()
            self._cache_timestamp = current_time

            # Build unified geometry for fast intersection calculations
            self._build_geometry_index()

    def _build_geometry_index(self) -> None:
        """Build a spatial index from bike lane features for fast intersection.

        Only includes REAL bike infrastructure (Class I, II, IV).
        Excludes Class III "Bike Routes" which are just sharrows on regular roads.
        """
        if not self._bike_lanes_cache:
            return

        features = self._bike_lanes_cache.get("features", [])
        if not features:
            logger.warning("No bike lane features found in SF data")
            return

        geometries = []
        excluded_count = 0
        included_by_type = {}

        for feature in features:
            try:
                props = feature.get("properties", {})
                facility_type = props.get("facility_t", "")

                # Only include real bike lanes, not CLASS III bike routes (sharrows)
                if facility_type not in REAL_BIKE_LANE_TYPES:
                    excluded_count += 1
                    continue

                geom = feature.get("geometry")
                if geom:
                    shapely_geom = shape(geom)
                    if shapely_geom.is_valid:
                        geometries.append(shapely_geom)
                        included_by_type[facility_type] = included_by_type.get(facility_type, 0) + 1
            except Exception as e:
                logger.debug(f"Failed to parse bike lane geometry: {e}")
                continue

        if geometries:
            # Combine all bike lanes into a single geometry for distance calculations
            self._bike_lanes_geometry = unary_union(geometries)
            # Create prepared geometry for faster intersection checks
            self._prepared_geometry = prepared.prep(self._bike_lanes_geometry)
            logger.info(
                f"Built bike lane index with {len(geometries)} real bike lane features "
                f"(excluded {excluded_count} sharrows/bike routes). "
                f"Types: {included_by_type}"
            )
        else:
            self._bike_lanes_geometry = None
            self._prepared_geometry = None

    async def calculate_bike_lane_percentage(
        self,
        route_coordinates: List[List[float]],
        max_distance_meters: float = 25.0,
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate accurate bike lane percentage by measuring distance to bike lanes.

        For each segment of the route, checks multiple points along the segment
        to determine if it follows a bike lane.

        Args:
            route_coordinates: List of [lon, lat] coordinates from route geometry
            max_distance_meters: Maximum distance to bike lane to count as "on bike lane"
                                 25m accounts for street width and coordinate discrepancies

        Returns:
            Tuple of (bike_lane_percentage, stats_dict)
        """
        if not route_coordinates or len(route_coordinates) < 2:
            return 0.0, {}

        await self._ensure_cache()

        if self._bike_lanes_geometry is None:
            logger.warning("No bike lane geometry available for intersection")
            return 0.0, {}

        try:
            from shapely.geometry import Point, LineString

            # Convert max distance from meters to degrees
            # At SF latitude (~37.7): 1 degree lat ≈ 111km, 1 degree lon ≈ 88km
            # Use 90km average for SF area for more accurate conversion
            max_distance_degrees = max_distance_meters / 90000

            total_distance = 0.0
            bike_lane_distance = 0.0
            segments_checked = 0
            segments_on_bike_lane = 0
            distance_samples = []

            # Check each segment of the route individually
            for i in range(len(route_coordinates) - 1):
                coord1 = route_coordinates[i]
                coord2 = route_coordinates[i + 1]

                # Calculate segment length in meters
                segment_length = self._haversine_distance(
                    coord1[1], coord1[0], coord2[1], coord2[0]
                )
                total_distance += segment_length
                segments_checked += 1

                # Check multiple points along the segment for better accuracy
                # Check start, 1/3, 2/3, and end points
                check_points = [
                    (coord1[0], coord1[1]),
                    (coord1[0] + (coord2[0] - coord1[0]) * 0.33, coord1[1] + (coord2[1] - coord1[1]) * 0.33),
                    (coord1[0] + (coord2[0] - coord1[0]) * 0.67, coord1[1] + (coord2[1] - coord1[1]) * 0.67),
                    (coord2[0], coord2[1]),
                ]

                # Count how many check points are near a bike lane
                points_on_bike_lane = 0
                min_distance = float('inf')

                for lon, lat in check_points:
                    point = Point(lon, lat)
                    distance_to_bike_lane = point.distance(self._bike_lanes_geometry)
                    min_distance = min(min_distance, distance_to_bike_lane)
                    if distance_to_bike_lane <= max_distance_degrees:
                        points_on_bike_lane += 1

                # Convert min distance to meters for debugging
                distance_meters = min_distance * 90000

                # Sample some distances for debugging
                if i % 20 == 0:
                    distance_samples.append(round(distance_meters, 1))

                # If majority of points are on bike lane, count the whole segment
                # (at least 2 of 4 points = 50% threshold)
                if points_on_bike_lane >= 2:
                    bike_lane_distance += segment_length
                    segments_on_bike_lane += 1

            if total_distance == 0:
                return 0.0, {}

            # Calculate percentage
            bike_lane_percentage = (bike_lane_distance / total_distance) * 100
            bike_lane_percentage = min(100.0, max(0.0, bike_lane_percentage))

            stats = {
                "total_distance_m": total_distance,
                "bike_lane_distance_m": bike_lane_distance,
                "road_distance_m": total_distance - bike_lane_distance,
                "segments_checked": segments_checked,
                "segments_on_bike_lane": segments_on_bike_lane,
            }

            logger.info(
                f"Bike lane calculation: {bike_lane_percentage:.1f}% "
                f"({bike_lane_distance:.0f}m of {total_distance:.0f}m on bike lanes, "
                f"{segments_on_bike_lane}/{segments_checked} segments, threshold={max_distance_meters}m). "
                f"Sample min distances (m): {distance_samples[:10]}"
            )

            return round(bike_lane_percentage, 1), stats

        except Exception as e:
            logger.error(f"Error calculating bike lane intersection: {e}")
            return 0.0, {}

    def _haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points using Haversine formula."""
        import math

        R = 6371000  # Earth radius in meters

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _calculate_length_meters(self, geometry) -> float:
        """Calculate approximate length of geometry in meters.

        Uses Haversine-based calculation for accuracy at SF latitudes.
        """
        import math

        if geometry.is_empty:
            return 0.0

        # Handle different geometry types
        if geometry.geom_type == "LineString":
            coords = list(geometry.coords)
        elif geometry.geom_type == "MultiLineString":
            coords = []
            for line in geometry.geoms:
                coords.extend(list(line.coords))
        elif geometry.geom_type == "GeometryCollection":
            total = 0.0
            for geom in geometry.geoms:
                total += self._calculate_length_meters(geom)
            return total
        else:
            # For polygons or other types, use the exterior or just return 0
            return 0.0

        if len(coords) < 2:
            return 0.0

        total_distance = 0.0
        R = 6371000  # Earth radius in meters

        for i in range(len(coords) - 1):
            lon1, lat1 = coords[i][:2]
            lon2, lat2 = coords[i + 1][:2]

            # Haversine formula
            lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)

            a = (
                math.sin(dlat / 2) ** 2
                + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
            )
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            total_distance += R * c

        return total_distance

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


# Singleton instance
bike_lane_service = BikeLaneService()
