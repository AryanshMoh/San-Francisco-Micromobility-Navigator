"""Generate risk zones from SF collision data - Neighborhood bubbles."""

import asyncio
import json
import math
from collections import defaultdict
from typing import Dict, List, Tuple
from uuid import uuid4

import httpx

# SF Collision Data API
SF_COLLISIONS_API = "https://data.sfgov.org/resource/ubvf-ztfx.json"

# Grid size for finding hotspots within neighborhoods (approximately 200m x 200m)
GRID_SIZE = 0.002

# Risk thresholds - minimum 160 accidents (no green, start with yellow)
THRESHOLD_MIN = 160
THRESHOLD_YELLOW_MAX = 199
# 200+ is red

# Max circles per neighborhood
MAX_CIRCLES_PER_NEIGHBORHOOD = 5


def get_grid_cell(lat: float, lon: float) -> Tuple[int, int]:
    """Get grid cell indices for a coordinate."""
    lat_idx = int(lat / GRID_SIZE)
    lon_idx = int(lon / GRID_SIZE)
    return (lat_idx, lon_idx)


def get_cell_center(lat_idx: int, lon_idx: int) -> Tuple[float, float]:
    """Get center coordinates of a grid cell."""
    lat = (lat_idx + 0.5) * GRID_SIZE
    lon = (lon_idx + 0.5) * GRID_SIZE
    return (lat, lon)


def get_severity(count: int) -> str:
    """Get severity level based on accident count."""
    if count <= THRESHOLD_YELLOW_MAX:
        return "MEDIUM"  # Yellow: 160-199
    else:
        return "HIGH"    # Red: 200+


def get_radius_meters(count: int) -> int:
    """Calculate bubble radius based on crash count.

    Minimum: 100m for 65 crashes
    Maximum: 500m for 300+ crashes
    """
    min_radius = 100
    max_radius = 500
    min_count = THRESHOLD_MIN
    max_count = 300

    # Linear interpolation
    normalized = min(1.0, max(0.0, (count - min_count) / (max_count - min_count)))
    radius = min_radius + normalized * (max_radius - min_radius)
    return int(radius)


async def fetch_collisions() -> List[Dict]:
    """Fetch all collision data from SF Open Data."""
    all_collisions = []
    offset = 0
    limit = 10000

    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            url = (
                f"{SF_COLLISIONS_API}?$limit={limit}&$offset={offset}"
                f"&$select=tb_latitude,tb_longitude,collision_severity,analysis_neighborhood"
            )
            print(f"Fetching collisions offset={offset}...")

            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            if not data:
                break

            all_collisions.extend(data)
            offset += limit

            if len(data) < limit:
                break

    print(f"Total collisions fetched: {len(all_collisions)}")
    return all_collisions


def aggregate_by_neighborhood_and_grid(collisions: List[Dict]) -> Dict[str, Dict[Tuple[int, int], Dict]]:
    """Aggregate collisions by neighborhood and grid cell."""
    neighborhood_grids = defaultdict(lambda: defaultdict(lambda: {
        "count": 0, "fatal": 0, "injury": 0, "lats": [], "lons": []
    }))

    for collision in collisions:
        try:
            lat = float(collision.get("tb_latitude", 0))
            lon = float(collision.get("tb_longitude", 0))
            neighborhood = collision.get("analysis_neighborhood", "Unknown")

            if not neighborhood or lat == 0 or lon == 0:
                continue

            cell = get_grid_cell(lat, lon)
            grid = neighborhood_grids[neighborhood][cell]
            grid["count"] += 1
            grid["lats"].append(lat)
            grid["lons"].append(lon)

            severity = collision.get("collision_severity", "")
            if severity == "Fatal":
                grid["fatal"] += 1
            elif "Injury" in severity:
                grid["injury"] += 1

        except (ValueError, TypeError):
            continue

    return neighborhood_grids


def generate_risk_zones(neighborhood_grids: Dict[str, Dict[Tuple[int, int], Dict]]) -> List[Dict]:
    """Generate risk zone records - max 5 bubbles per neighborhood."""
    risk_zones = []

    for neighborhood, grid_cells in neighborhood_grids.items():
        # Filter cells with minimum threshold
        high_risk_cells = [
            (cell, data) for cell, data in grid_cells.items()
            if data["count"] >= THRESHOLD_MIN
        ]

        if not high_risk_cells:
            continue

        # Sort by count descending and take top 5
        high_risk_cells.sort(key=lambda x: x[1]["count"], reverse=True)
        top_cells = high_risk_cells[:MAX_CIRCLES_PER_NEIGHBORHOOD]

        for cell, data in top_cells:
            count = data["count"]

            # Calculate center from actual collision coordinates
            center_lat = sum(data["lats"]) / len(data["lats"])
            center_lon = sum(data["lons"]) / len(data["lons"])

            severity = get_severity(count)
            radius = get_radius_meters(count)

            # Determine hazard type
            if data["fatal"] > 0:
                hazard_type = "HIGH_TRAFFIC"
            elif data["injury"] > 10:
                hazard_type = "DANGEROUS_INTERSECTION"
            else:
                hazard_type = "HIGH_TRAFFIC"

            risk_zone = {
                "id": str(uuid4()),
                "geometry": {
                    "type": "Point",
                    "coordinates": [center_lon, center_lat],
                },
                "hazard_type": hazard_type,
                "severity": severity,
                "name": f"{neighborhood} ({count} crashes)",
                "description": f"{count} traffic incidents in {neighborhood}. "
                              f"Fatal: {data['fatal']}, Injuries: {data['injury']}",
                "accident_count": count,
                "neighborhood": neighborhood,
                "radius_meters": radius,
                "fatal_count": data["fatal"],
                "injury_count": data["injury"],
                "center_lat": center_lat,
                "center_lon": center_lon,
            }

            risk_zones.append(risk_zone)

    # Sort by count descending
    risk_zones.sort(key=lambda x: x["accident_count"], reverse=True)

    # Print summary
    print(f"\nRisk zone summary:")
    print(f"  Yellow (160-199 crashes): {sum(1 for z in risk_zones if z['severity'] == 'MEDIUM')}")
    print(f"  Red (200+ crashes): {sum(1 for z in risk_zones if z['severity'] == 'HIGH')}")
    print(f"  Total risk zones: {len(risk_zones)}")

    # Print by neighborhood
    print(f"\nZones per neighborhood:")
    neighborhood_counts = defaultdict(int)
    for zone in risk_zones:
        neighborhood_counts[zone["neighborhood"]] += 1
    for n, c in sorted(neighborhood_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {n}: {c} zones")

    return risk_zones


def generate_sql_inserts(risk_zones: List[Dict]) -> str:
    """Generate SQL INSERT statements for risk zones."""
    sql_lines = [
        "-- Risk zones generated from SF collision data (neighborhood bubbles)",
        "-- Minimum 65 crashes, max 5 per neighborhood",
        "-- Clear existing risk zones",
        "DELETE FROM risk_zones;",
        "",
        "-- Insert new risk zones",
    ]

    for zone in risk_zones:
        # Point geometry
        lon, lat = zone["geometry"]["coordinates"]
        sql = f"""INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    '{zone["id"]}',
    ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326),
    '{zone["hazard_type"]}',
    '{zone["severity"]}',
    '{zone["name"].replace("'", "''")}',
    '{zone["description"].replace("'", "''")}',
    true,
    {zone["radius_meters"]},
    'MUNICIPAL',
    0.95,
    {zone["accident_count"]},
    true
);"""
        sql_lines.append(sql)

    return "\n".join(sql_lines)


def generate_geojson(risk_zones: List[Dict]) -> Dict:
    """Generate GeoJSON FeatureCollection for visualization."""
    features = []

    for zone in risk_zones:
        feature = {
            "type": "Feature",
            "geometry": zone["geometry"],
            "properties": {
                "id": zone["id"],
                "severity": zone["severity"],
                "accident_count": zone["accident_count"],
                "neighborhood": zone["neighborhood"],
                "radius_meters": zone["radius_meters"],
                "fatal_count": zone["fatal_count"],
                "injury_count": zone["injury_count"],
                "name": zone["name"],
                "description": zone["description"],
            },
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


async def main():
    print("Fetching SF collision data...")
    collisions = await fetch_collisions()

    print("\nAggregating by neighborhood and grid cells...")
    neighborhood_grids = aggregate_by_neighborhood_and_grid(collisions)
    print(f"Total neighborhoods: {len(neighborhood_grids)}")

    print(f"\nGenerating risk zones (min {THRESHOLD_MIN} crashes, max {MAX_CIRCLES_PER_NEIGHBORHOOD} per neighborhood)...")
    risk_zones = generate_risk_zones(neighborhood_grids)

    # Save SQL file
    sql = generate_sql_inserts(risk_zones)
    with open("risk_zones.sql", "w") as f:
        f.write(sql)
    print(f"\nSQL file saved: risk_zones.sql")

    # Save GeoJSON for frontend
    geojson = generate_geojson(risk_zones)
    with open("risk_zones.geojson", "w") as f:
        json.dump(geojson, f)
    print(f"GeoJSON file saved: risk_zones.geojson")

    # Print top 10 highest risk zones
    print("\nTop 10 highest risk zones:")
    for zone in risk_zones[:10]:
        print(f"  {zone['accident_count']} crashes - {zone['name']} (radius: {zone['radius_meters']}m)")


if __name__ == "__main__":
    asyncio.run(main())
