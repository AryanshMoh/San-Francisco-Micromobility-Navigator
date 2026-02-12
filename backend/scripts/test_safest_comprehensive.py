"""Comprehensive test for SAFEST routing to completely avoid risk zones.

This script tests 50+ routes that MUST pass through risk zone areas,
measuring how well SAFEST routing avoids them.
"""

import asyncio
import json
import math
from typing import List, Dict, Tuple
from collections import defaultdict

import httpx

API_BASE = "http://localhost:8000"

# Risk zone data (will be fetched)
RISK_ZONES = []

# Risk zone centers for strategic test case generation
# These are the actual risk zone locations from the database
RISK_ZONE_CENTERS = [
    # High-risk Tenderloin area
    {"name": "Tenderloin-1", "lat": 37.783104, "lon": -122.414898, "crashes": 294},
    {"name": "Tenderloin-2", "lat": 37.785056, "lon": -122.419477, "crashes": 260},
    {"name": "Tenderloin-3", "lat": 37.784806, "lon": -122.417002, "crashes": 210},
    {"name": "Tenderloin-4", "lat": 37.786568, "lon": -122.418926, "crashes": 204},
    {"name": "Tenderloin-5", "lat": 37.782933, "lon": -122.412552, "crashes": 198},
    # South of Market (SoMa)
    {"name": "SoMa-1", "lat": 37.781056, "lon": -122.408877, "crashes": 297},
    {"name": "SoMa-2", "lat": 37.777229, "lon": -122.412912, "crashes": 189},
    {"name": "SoMa-3", "lat": 37.774968, "lon": -122.415196, "crashes": 168},
    # Mission District
    {"name": "Mission-1", "lat": 37.765380, "lon": -122.407336, "crashes": 241},
    {"name": "Mission-2", "lat": 37.769294, "lon": -122.417714, "crashes": 220},
    {"name": "Mission-3", "lat": 37.773001, "lon": -122.418673, "crashes": 208},
    {"name": "Mission-4", "lat": 37.771718, "lon": -122.423257, "crashes": 208},
    {"name": "Mission-5", "lat": 37.769222, "lon": -122.422457, "crashes": 203},
    # Financial District
    {"name": "FiDi-1", "lat": 37.787227, "lon": -122.403024, "crashes": 229},
    {"name": "FiDi-2", "lat": 37.789002, "lon": -122.402811, "crashes": 200},
    # Hayes Valley
    {"name": "Hayes-1", "lat": 37.773101, "lon": -122.423121, "crashes": 207},
    {"name": "Hayes-2", "lat": 37.774929, "lon": -122.424589, "crashes": 188},
    # Western Addition
    {"name": "Western-1", "lat": 37.781075, "lon": -122.422970, "crashes": 207},
    {"name": "Western-2", "lat": 37.779279, "lon": -122.430842, "crashes": 193},
    # Nob Hill
    {"name": "NobHill", "lat": 37.789016, "lon": -122.420844, "crashes": 188},
    # Castro
    {"name": "Castro", "lat": 37.767272, "lon": -122.428954, "crashes": 166},
]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two points."""
    R = 6371000
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def point_between(p1: Tuple[float, float], p2: Tuple[float, float],
                  zone: Dict, threshold_m: float = 500) -> bool:
    """Check if a risk zone is roughly between two points."""
    zone_lat, zone_lon = zone["lat"], zone["lon"]

    # Zone should be within bounding box of p1 and p2 (with buffer)
    min_lat = min(p1[0], p2[0]) - 0.005
    max_lat = max(p1[0], p2[0]) + 0.005
    min_lon = min(p1[1], p2[1]) - 0.005
    max_lon = max(p1[1], p2[1]) + 0.005

    if not (min_lat <= zone_lat <= max_lat and min_lon <= zone_lon <= max_lon):
        return False

    # Zone should be reasonably close to the line between p1 and p2
    # Use perpendicular distance approximation
    d1 = haversine_distance(p1[0], p1[1], zone_lat, zone_lon)
    d2 = haversine_distance(p2[0], p2[1], zone_lat, zone_lon)
    d12 = haversine_distance(p1[0], p1[1], p2[0], p2[1])

    # If zone is roughly on the path (d1 + d2 ~ d12)
    if d12 > 0:
        detour_ratio = (d1 + d2) / d12
        return detour_ratio < 1.5  # Allow 50% detour

    return False


def count_zones_between(p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    """Count how many risk zones are between two points."""
    count = 0
    for zone in RISK_ZONE_CENTERS:
        if point_between(p1, p2, zone):
            count += 1
    return count


def generate_strategic_test_cases() -> List[Tuple[Tuple[float, float], Tuple[float, float], str]]:
    """Generate test cases that specifically cross through risk zones."""
    test_cases = []

    # Group 1: Routes THROUGH Tenderloin (highest risk area)
    tenderloin_through = [
        # North to South through Tenderloin
        ((37.795, -122.42), (37.77, -122.41), "N-S through Tenderloin"),
        ((37.793, -122.415), (37.775, -122.415), "N-S Tenderloin center"),
        ((37.80, -122.42), (37.765, -122.42), "N-S deep Tenderloin"),
        # West to East through Tenderloin
        ((37.785, -122.43), (37.785, -122.40), "W-E through Tenderloin"),
        ((37.783, -122.425), (37.783, -122.405), "W-E Tenderloin low"),
        ((37.787, -122.43), (37.787, -122.40), "W-E Tenderloin high"),
        # Diagonal through Tenderloin
        ((37.795, -122.43), (37.77, -122.40), "NW-SE through Tenderloin"),
        ((37.795, -122.40), (37.77, -122.43), "NE-SW through Tenderloin"),
        ((37.79, -122.425), (37.78, -122.405), "Diagonal Tenderloin short"),
    ]
    test_cases.extend([(o, d, f"Tenderloin: {n}") for o, d, n in tenderloin_through])

    # Group 2: Routes THROUGH SoMa
    soma_through = [
        ((37.79, -122.42), (37.765, -122.40), "N-S through SoMa"),
        ((37.785, -122.415), (37.77, -122.40), "NW-SE through SoMa"),
        ((37.79, -122.395), (37.77, -122.42), "NE-SW through SoMa"),
        ((37.785, -122.42), (37.775, -122.395), "W-E through SoMa"),
        ((37.79, -122.41), (37.77, -122.41), "N-S SoMa direct"),
    ]
    test_cases.extend([(o, d, f"SoMa: {n}") for o, d, n in soma_through])

    # Group 3: Routes THROUGH Mission District
    mission_through = [
        ((37.785, -122.43), (37.755, -122.40), "N-S through Mission"),
        ((37.78, -122.425), (37.76, -122.405), "NW-SE Mission"),
        ((37.775, -122.43), (37.765, -122.40), "W-E through Mission"),
        ((37.78, -122.41), (37.755, -122.43), "NE-SW through Mission"),
        ((37.775, -122.425), (37.76, -122.415), "Mission center"),
    ]
    test_cases.extend([(o, d, f"Mission: {n}") for o, d, n in mission_through])

    # Group 4: Routes THROUGH Financial District
    fidi_through = [
        ((37.795, -122.41), (37.78, -122.395), "N-S through FiDi"),
        ((37.79, -122.415), (37.785, -122.395), "W-E through FiDi"),
        ((37.795, -122.42), (37.775, -122.39), "NW-SE through FiDi"),
    ]
    test_cases.extend([(o, d, f"FiDi: {n}") for o, d, n in fidi_through])

    # Group 5: Cross-neighborhood routes (through multiple zones)
    cross_neighborhood = [
        # Marina to Mission (through Tenderloin & SoMa)
        ((37.80, -122.44), (37.755, -122.41), "Marina to Mission"),
        # Pacific Heights to Potrero (through Tenderloin, SoMa)
        ((37.79, -122.44), (37.76, -122.395), "Pac Heights to Potrero"),
        # North Beach to Castro (through Tenderloin, Hayes)
        ((37.80, -122.41), (37.76, -122.435), "North Beach to Castro"),
        # Fisherman's Wharf to Bernal (through FiDi, SoMa, Mission)
        ((37.808, -122.42), (37.745, -122.41), "Wharf to Bernal"),
        # Russian Hill to Glen Park
        ((37.80, -122.42), (37.735, -122.435), "Russian Hill to Glen Park"),
        # Presidio to Dogpatch
        ((37.79, -122.46), (37.76, -122.385), "Presidio to Dogpatch"),
        # Inner Richmond to SOMA
        ((37.78, -122.47), (37.775, -122.405), "Richmond to SoMa"),
        # Haight to Embarcadero
        ((37.77, -122.45), (37.795, -122.39), "Haight to Embarcadero"),
    ]
    test_cases.extend([(o, d, f"Cross: {n}") for o, d, n in cross_neighborhood])

    # Group 6: Routes through Hayes Valley / Western Addition
    hayes_through = [
        ((37.785, -122.44), (37.77, -122.41), "N-S through Hayes"),
        ((37.78, -122.435), (37.775, -122.415), "W-E through Hayes"),
        ((37.785, -122.43), (37.765, -122.42), "Diagonal Hayes"),
    ]
    test_cases.extend([(o, d, f"Hayes: {n}") for o, d, n in hayes_through])

    # Group 7: Short routes within high-risk zones
    short_high_risk = [
        # Within Tenderloin
        ((37.786, -122.418), (37.782, -122.412), "Short Tenderloin"),
        ((37.785, -122.42), (37.783, -122.415), "Short Tenderloin 2"),
        # Within SoMa
        ((37.782, -122.41), (37.777, -122.405), "Short SoMa"),
        ((37.78, -122.412), (37.775, -122.408), "Short SoMa 2"),
        # Within Mission
        ((37.77, -122.42), (37.765, -122.415), "Short Mission"),
        ((37.772, -122.418), (37.768, -122.422), "Short Mission 2"),
    ]
    test_cases.extend([(o, d, f"Short: {n}") for o, d, n in short_high_risk])

    # Group 8: Edge-to-edge across the danger zone
    edge_to_edge = [
        # Full west to east
        ((37.78, -122.45), (37.78, -122.39), "Full W-E at 37.78"),
        ((37.785, -122.45), (37.785, -122.39), "Full W-E at 37.785"),
        # Full north to south
        ((37.81, -122.42), (37.74, -122.42), "Full N-S at -122.42"),
        ((37.81, -122.41), (37.74, -122.41), "Full N-S at -122.41"),
    ]
    test_cases.extend([(o, d, f"Edge: {n}") for o, d, n in edge_to_edge])

    # Group 9: Additional cross-risk-zone routes
    more_cross = [
        # Golden Gate Park to Downtown
        ((37.77, -122.48), (37.785, -122.41), "GG Park to Downtown"),
        ((37.765, -122.47), (37.79, -122.405), "Sunset to FiDi"),
        # Presidio to Mission
        ((37.795, -122.465), (37.76, -122.415), "Presidio to Mission"),
        # Twin Peaks to Embarcadero
        ((37.755, -122.445), (37.795, -122.395), "Twin Peaks to Embarcadero"),
        # Outer Richmond to Potrero
        ((37.78, -122.505), (37.76, -122.39), "O Richmond to Potrero"),
        # Sea Cliff to SOMA
        ((37.785, -122.49), (37.775, -122.405), "Sea Cliff to SoMa"),
        # Forest Hill to North Beach
        ((37.745, -122.46), (37.80, -122.41), "Forest Hill to N Beach"),
    ]
    test_cases.extend([(o, d, f"XRisk: {n}") for o, d, n in more_cross])

    # Group 10: Routes through multiple risk clusters
    multi_cluster = [
        # Through Tenderloin AND SoMa
        ((37.795, -122.425), (37.765, -122.395), "Through TL + SoMa"),
        # Through Mission AND Hayes
        ((37.755, -122.435), (37.785, -122.405), "Through Mission + Hayes"),
        # Through FiDi AND Tenderloin
        ((37.80, -122.395), (37.775, -122.425), "Through FiDi + TL"),
        # Full gauntlet: Tenderloin, SoMa, Mission
        ((37.80, -122.425), (37.745, -122.41), "Gauntlet: TL-SoMa-Mission"),
    ]
    test_cases.extend([(o, d, f"Multi: {n}") for o, d, n in multi_cluster])

    return test_cases


async def fetch_risk_zones(client: httpx.AsyncClient):
    """Fetch risk zones from API."""
    global RISK_ZONES
    response = await client.get(f"{API_BASE}/api/v1/risk-zones?bbox=-122.52,37.70,-122.35,37.82")
    zones = response.json()
    RISK_ZONES = [
        {
            'id': z.get('id'),
            'coordinates': (z['geometry']['coordinates'][0], z['geometry']['coordinates'][1]),
            'radius': z['alert_radius_meters'],
            'crashes': z['reported_count'],
            'severity': z['severity'],
        }
        for z in zones
    ]
    print(f"Loaded {len(RISK_ZONES)} risk zones")


def count_risk_zone_passes(route_coords: List[List[float]], threshold_m: float = 100) -> Tuple[int, float]:
    """Count how many times route passes within threshold of a risk zone.

    Returns: (num_passes, min_distance_to_any_zone)
    """
    passes = 0
    min_distance = float('inf')

    for coord in route_coords:
        lon, lat = coord[0], coord[1]
        for zone in RISK_ZONES:
            zone_lon, zone_lat = zone['coordinates']
            zone_radius = zone['radius']
            dist = haversine_distance(lat, lon, zone_lat, zone_lon)
            min_distance = min(min_distance, dist)

            # Count as "pass" if within zone radius
            if dist < zone_radius:
                passes += 1
                break

    return passes, min_distance


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
        print(f"Error: {e}")
        return None


async def run_test(client: httpx.AsyncClient, test_num: int,
                   origin: Tuple[float, float], dest: Tuple[float, float],
                   description: str) -> Dict:
    """Run a single test comparing SAFEST vs FASTEST."""

    safest_route = await calculate_route(client, origin, dest, "safest")
    fastest_route = await calculate_route(client, origin, dest, "fastest")

    if not safest_route or not fastest_route:
        return None

    safest_coords = safest_route['geometry']['coordinates']
    fastest_coords = fastest_route['geometry']['coordinates']

    safest_passes, safest_min_dist = count_risk_zone_passes(safest_coords)
    fastest_passes, fastest_min_dist = count_risk_zone_passes(fastest_coords)

    # Calculate improvement
    if fastest_passes > 0:
        improvement = ((fastest_passes - safest_passes) / fastest_passes) * 100
    else:
        improvement = 0 if safest_passes == 0 else -100

    result = {
        'test_num': test_num,
        'description': description,
        'origin': origin,
        'dest': dest,
        'safest': {
            'distance_m': safest_route['summary']['distance_meters'],
            'zone_passes': safest_passes,
            'min_dist_to_zone': round(safest_min_dist, 1),
        },
        'fastest': {
            'distance_m': fastest_route['summary']['distance_meters'],
            'zone_passes': fastest_passes,
            'min_dist_to_zone': round(fastest_min_dist, 1),
        },
        'improvement_pct': round(improvement, 1),
        'safest_avoids': safest_passes == 0,
        'safest_better': safest_passes < fastest_passes or (safest_passes == fastest_passes and safest_min_dist > fastest_min_dist),
    }

    return result


async def main():
    print("=" * 70)
    print("COMPREHENSIVE SAFEST ROUTING TEST")
    print("Goal: SAFEST profile should COMPLETELY avoid risk zones")
    print("=" * 70)

    async with httpx.AsyncClient(timeout=60.0) as client:
        await fetch_risk_zones(client)

        test_cases = generate_strategic_test_cases()
        print(f"\nGenerated {len(test_cases)} strategic test cases\n")

        results = []
        by_category = defaultdict(list)

        complete_avoidance = 0
        safest_better = 0
        same_result = 0
        fastest_better = 0

        for i, (origin, dest, desc) in enumerate(test_cases):
            result = await run_test(client, i + 1, origin, dest, desc)
            if result:
                results.append(result)

                # Categorize
                category = desc.split(":")[0] if ":" in desc else "Other"
                by_category[category].append(result)

                s = result['safest']
                f = result['fastest']

                # Count outcomes
                if s['zone_passes'] == 0:
                    complete_avoidance += 1
                    status = "✓ COMPLETE AVOIDANCE"
                elif s['zone_passes'] < f['zone_passes']:
                    safest_better += 1
                    status = f"→ SAFEST better ({s['zone_passes']} vs {f['zone_passes']})"
                elif s['zone_passes'] == f['zone_passes']:
                    if s['min_dist_to_zone'] > f['min_dist_to_zone']:
                        safest_better += 1
                        status = "→ SAFEST farther from zones"
                    elif s['min_dist_to_zone'] < f['min_dist_to_zone']:
                        fastest_better += 1
                        status = "✗ FASTEST farther"
                    else:
                        same_result += 1
                        status = "= SAME"
                else:
                    fastest_better += 1
                    status = f"✗ FASTEST better ({f['zone_passes']} vs {s['zone_passes']})"

                print(f"Test {i+1:2d} [{desc[:30]:30s}] {status}")

        # Summary
        total = len(results)
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Total tests: {total}")
        print(f"\n📊 OUTCOMES:")
        print(f"   ✓ Complete avoidance (0 zone passes): {complete_avoidance} ({complete_avoidance/total*100:.1f}%)")
        print(f"   → SAFEST avoids better: {safest_better} ({safest_better/total*100:.1f}%)")
        print(f"   = Same result: {same_result} ({same_result/total*100:.1f}%)")
        print(f"   ✗ FASTEST avoids better: {fastest_better} ({fastest_better/total*100:.1f}%)")

        # Calculate averages
        avg_safest_passes = sum(r['safest']['zone_passes'] for r in results) / total
        avg_fastest_passes = sum(r['fastest']['zone_passes'] for r in results) / total

        print(f"\n📈 ZONE PASSES:")
        print(f"   SAFEST average: {avg_safest_passes:.1f}")
        print(f"   FASTEST average: {avg_fastest_passes:.1f}")
        if avg_fastest_passes > 0:
            reduction = ((avg_fastest_passes - avg_safest_passes) / avg_fastest_passes) * 100
            print(f"   Reduction: {reduction:.1f}%")

        # By category breakdown
        print(f"\n📋 BY CATEGORY:")
        for category, cat_results in sorted(by_category.items()):
            cat_total = len(cat_results)
            cat_complete = sum(1 for r in cat_results if r['safest']['zone_passes'] == 0)
            cat_avg_safest = sum(r['safest']['zone_passes'] for r in cat_results) / cat_total
            cat_avg_fastest = sum(r['fastest']['zone_passes'] for r in cat_results) / cat_total
            print(f"   {category:15s}: {cat_total:2d} tests, {cat_complete} complete avoidance, "
                  f"avg passes: {cat_avg_safest:.1f} vs {cat_avg_fastest:.1f}")

        # Identify problem cases
        problem_cases = [r for r in results if r['safest']['zone_passes'] > 0 and
                         r['safest']['zone_passes'] >= r['fastest']['zone_passes']]
        if problem_cases:
            print(f"\n⚠️  PROBLEM CASES (SAFEST not avoiding):")
            for r in problem_cases[:10]:
                print(f"   Test {r['test_num']}: {r['description']}")
                print(f"      SAFEST: {r['safest']['zone_passes']} passes, "
                      f"FASTEST: {r['fastest']['zone_passes']} passes")

        # Success metric
        success_rate = (complete_avoidance + safest_better) / total * 100
        print(f"\n🎯 SUCCESS RATE: {success_rate:.1f}%")
        print(f"   (Complete avoidance + SAFEST better)")

        if success_rate >= 80:
            print("\n✅ EXCELLENT - SAFEST routing effectively avoids risk zones!")
        elif success_rate >= 60:
            print("\n⚠️  GOOD - SAFEST routing mostly avoids risk zones, room for improvement")
        else:
            print("\n❌ NEEDS IMPROVEMENT - SAFEST routing not effectively avoiding risk zones")


if __name__ == "__main__":
    asyncio.run(main())
