"""Test routing to verify SAFEST profile avoids risk zones."""

import asyncio
import json
import math
import random
from typing import List, Dict, Tuple

import httpx

API_BASE = "http://localhost:8000"

# SF bounding box for random points
SF_BOUNDS = {
    "min_lat": 37.72,
    "max_lat": 37.80,
    "min_lon": -122.48,
    "max_lon": -122.38,
}

# Risk zone data (will be fetched)
RISK_ZONES = []


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two points."""
    R = 6371000  # Earth radius in meters
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def get_min_distance_to_risk_zones(route_coords: List[List[float]]) -> Tuple[float, int]:
    """Calculate minimum distance from route to any risk zone.

    Returns: (min_distance_meters, num_zones_within_100m)
    """
    min_distance = float('inf')
    zones_within_100m = 0

    for coord in route_coords:
        lon, lat = coord[0], coord[1]
        for zone in RISK_ZONES:
            zone_lon, zone_lat = zone['coordinates']
            dist = haversine_distance(lat, lon, zone_lat, zone_lon)
            min_distance = min(min_distance, dist)
            if dist < 100:
                zones_within_100m += 1
                break  # Count each route point only once

    return min_distance, zones_within_100m


def count_risk_zone_passes(route_coords: List[List[float]], threshold_m: float = 150) -> int:
    """Count how many times route passes within threshold of a risk zone."""
    passes = 0
    for coord in route_coords:
        lon, lat = coord[0], coord[1]
        for zone in RISK_ZONES:
            zone_lon, zone_lat = zone['coordinates']
            zone_radius = zone['radius']
            dist = haversine_distance(lat, lon, zone_lat, zone_lon)
            if dist < zone_radius + threshold_m:
                passes += 1
                break
    return passes


async def fetch_risk_zones(client: httpx.AsyncClient):
    """Fetch risk zones from API."""
    global RISK_ZONES
    response = await client.get(f"{API_BASE}/api/v1/risk-zones?bbox=-122.52,37.70,-122.35,37.82")
    zones = response.json()
    RISK_ZONES = [
        {
            'coordinates': (z['geometry']['coordinates'][0], z['geometry']['coordinates'][1]),
            'radius': z['alert_radius_meters'],
            'crashes': z['reported_count'],
            'severity': z['severity'],
        }
        for z in zones
    ]
    print(f"Loaded {len(RISK_ZONES)} risk zones")


async def calculate_route(client: httpx.AsyncClient, origin: Tuple[float, float],
                          dest: Tuple[float, float], profile: str) -> Dict:
    """Calculate a route and return results."""
    request = {
        "origin": {"latitude": origin[0], "longitude": origin[1]},
        "destination": {"latitude": dest[0], "longitude": dest[1]},
        "vehicle_type": "bike",
        "preferences": {
            "profile": profile,
            "prefer_bike_lanes": False
        }
    }

    try:
        response = await client.post(f"{API_BASE}/api/v1/routes/calculate", json=request)
        if response.status_code != 200:
            return None
        return response.json()
    except Exception as e:
        return None


def generate_random_point() -> Tuple[float, float]:
    """Generate a random point in SF."""
    lat = random.uniform(SF_BOUNDS["min_lat"], SF_BOUNDS["max_lat"])
    lon = random.uniform(SF_BOUNDS["min_lon"], SF_BOUNDS["max_lon"])
    return (lat, lon)


async def run_test(client: httpx.AsyncClient, test_num: int, origin: Tuple[float, float],
                   dest: Tuple[float, float]) -> Dict:
    """Run a single test comparing SAFEST vs FASTEST."""

    safest_route = await calculate_route(client, origin, dest, "safest")
    fastest_route = await calculate_route(client, origin, dest, "fastest")

    if not safest_route or not fastest_route:
        return None

    safest_coords = safest_route['geometry']['coordinates']
    fastest_coords = fastest_route['geometry']['coordinates']

    safest_min_dist, safest_zones_near = get_min_distance_to_risk_zones(safest_coords)
    fastest_min_dist, fastest_zones_near = get_min_distance_to_risk_zones(fastest_coords)

    safest_passes = count_risk_zone_passes(safest_coords)
    fastest_passes = count_risk_zone_passes(fastest_coords)

    result = {
        'test_num': test_num,
        'origin': origin,
        'dest': dest,
        'safest': {
            'distance_m': safest_route['summary']['distance_meters'],
            'duration_s': safest_route['summary']['duration_seconds'],
            'min_dist_to_zone': round(safest_min_dist, 1),
            'points_near_zones': safest_zones_near,
            'zone_passes': safest_passes,
        },
        'fastest': {
            'distance_m': fastest_route['summary']['distance_meters'],
            'duration_s': fastest_route['summary']['duration_seconds'],
            'min_dist_to_zone': round(fastest_min_dist, 1),
            'points_near_zones': fastest_zones_near,
            'zone_passes': fastest_passes,
        },
        'safest_avoids_better': safest_passes < fastest_passes or safest_min_dist > fastest_min_dist,
    }

    return result


async def main():
    print("=" * 60)
    print("RISK ZONE AVOIDANCE TEST - SAFEST vs FASTEST")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        await fetch_risk_zones(client)

        # Generate 35 test cases
        test_cases = []

        # Some strategic test cases that should pass through high-risk areas
        strategic_tests = [
            # Through Tenderloin
            ((37.79, -122.43), (37.78, -122.40)),
            ((37.785, -122.42), (37.78, -122.405)),
            # Through SoMa
            ((37.79, -122.41), (37.77, -122.40)),
            ((37.785, -122.415), (37.775, -122.395)),
            # Through Mission
            ((37.78, -122.43), (37.75, -122.41)),
            ((37.77, -122.425), (37.76, -122.405)),
            # Cross-city routes
            ((37.80, -122.45), (37.75, -122.38)),
            ((37.78, -122.48), (37.77, -122.38)),
            ((37.79, -122.44), (37.76, -122.40)),
            ((37.795, -122.46), (37.76, -122.395)),
        ]
        test_cases.extend(strategic_tests)

        # Add random test cases
        while len(test_cases) < 35:
            origin = generate_random_point()
            dest = generate_random_point()
            # Ensure minimum distance between origin and dest
            if haversine_distance(origin[0], origin[1], dest[0], dest[1]) > 1000:
                test_cases.append((origin, dest))

        results = []
        safest_better_count = 0
        same_count = 0
        fastest_better_count = 0

        print(f"\nRunning {len(test_cases)} test cases...\n")

        for i, (origin, dest) in enumerate(test_cases):
            result = await run_test(client, i + 1, origin, dest)
            if result:
                results.append(result)

                s = result['safest']
                f = result['fastest']

                # Determine which is better for avoiding risk zones
                if s['zone_passes'] < f['zone_passes']:
                    status = "SAFEST AVOIDS BETTER"
                    safest_better_count += 1
                elif s['zone_passes'] > f['zone_passes']:
                    status = "FASTEST AVOIDS BETTER (!)"
                    fastest_better_count += 1
                else:
                    if s['min_dist_to_zone'] > f['min_dist_to_zone']:
                        status = "SAFEST AVOIDS BETTER (farther)"
                        safest_better_count += 1
                    elif s['min_dist_to_zone'] < f['min_dist_to_zone']:
                        status = "FASTEST AVOIDS BETTER (farther) (!)"
                        fastest_better_count += 1
                    else:
                        status = "SAME"
                        same_count += 1

                print(f"Test {i+1:2d}: {status}")
                print(f"         SAFEST:  {s['distance_m']:5d}m, {s['zone_passes']:2d} zone passes, min dist: {s['min_dist_to_zone']:6.1f}m")
                print(f"         FASTEST: {f['distance_m']:5d}m, {f['zone_passes']:2d} zone passes, min dist: {f['min_dist_to_zone']:6.1f}m")

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        total = len(results)
        print(f"Total tests run: {total}")
        print(f"SAFEST avoids risk zones better: {safest_better_count} ({safest_better_count/total*100:.1f}%)")
        print(f"Same avoidance: {same_count} ({same_count/total*100:.1f}%)")
        print(f"FASTEST avoids better (unexpected): {fastest_better_count} ({fastest_better_count/total*100:.1f}%)")

        # Calculate averages
        avg_safest_passes = sum(r['safest']['zone_passes'] for r in results) / total
        avg_fastest_passes = sum(r['fastest']['zone_passes'] for r in results) / total
        avg_safest_min_dist = sum(r['safest']['min_dist_to_zone'] for r in results) / total
        avg_fastest_min_dist = sum(r['fastest']['min_dist_to_zone'] for r in results) / total

        print(f"\nAverage zone passes - SAFEST: {avg_safest_passes:.1f}, FASTEST: {avg_fastest_passes:.1f}")
        print(f"Average min distance to zone - SAFEST: {avg_safest_min_dist:.1f}m, FASTEST: {avg_fastest_min_dist:.1f}m")

        if avg_safest_passes < avg_fastest_passes:
            improvement = ((avg_fastest_passes - avg_safest_passes) / avg_fastest_passes) * 100
            print(f"\nSAFEST reduces zone passes by {improvement:.1f}% on average")


if __name__ == "__main__":
    asyncio.run(main())
