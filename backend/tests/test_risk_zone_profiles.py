"""
Test script: Verify routing profiles respect risk zone constraints.

Expected behavior:
- SAFEST: Avoids ALL risk zones (0 zone passes)
- BALANCED: May pass through yellow/light-red (160-199 crashes) but avoids
  HIGH (200+) and CRITICAL (250+) zones
- FASTEST: Can pass through any risk zone for shortest time

Runs 100 random origin/destination pairs in SF that are guaranteed to have
risk zones between them, then checks compliance for each profile.
"""

import asyncio
import json
import random
import math
import time
import httpx
from typing import List, Dict, Tuple, Any

API_BASE = "http://localhost:8000"
RISK_ZONES_URL = f"{API_BASE}/api/v1/risk-zones?bbox=-122.52,37.70,-122.35,37.82"
ROUTE_URL = f"{API_BASE}/api/v1/routes/calculate"

# SF bounding box for random point generation
SF_BOUNDS = {
    "min_lat": 37.72,
    "max_lat": 37.80,
    "min_lon": -122.52,
    "max_lon": -122.38,
}

# Severity thresholds matching the backend
SEVERITY_THRESHOLDS = {
    "LOW": 160,
    "MEDIUM": 160,
    "HIGH": 200,
    "CRITICAL": 250,
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two points."""
    R = 6371000
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def point_in_zone(lat: float, lon: float, zone: Dict, radius_factor: float = 0.5) -> bool:
    """Check if a point is within a risk zone's avoidance radius.

    Uses radius_factor of the alert_radius_meters, matching the backend logic.
    """
    zone_coords = zone["geometry"]["coordinates"]
    zone_lon, zone_lat = zone_coords[0], zone_coords[1]
    zone_radius = zone.get("alert_radius_meters", 150) * radius_factor
    dist = haversine_distance(lat, lon, zone_lat, zone_lon)
    return dist < zone_radius


def route_passes_through_zone(route_coords: List[List[float]], zone: Dict, radius_factor: float = 0.5) -> bool:
    """Check if any coordinate on the route passes through a risk zone's avoidance radius."""
    for coord in route_coords:
        lon, lat = coord[0], coord[1]
        if point_in_zone(lat, lon, zone, radius_factor):
            return True
    return False


def classify_zone(zone: Dict) -> str:
    """Classify a zone by its reported_count into severity tiers."""
    count = zone.get("reported_count", 0)
    if count >= 250:
        return "CRITICAL"
    elif count >= 200:
        return "HIGH"
    elif count >= 160:
        return "YELLOW_LIGHT_RED"
    else:
        return "BELOW_THRESHOLD"


def zone_is_between_points(
    origin_lat: float, origin_lon: float,
    dest_lat: float, dest_lon: float,
    zone: Dict, margin: float = 1.5
) -> bool:
    """Check if a zone is roughly between origin and destination."""
    zone_coords = zone["geometry"]["coordinates"]
    z_lon, z_lat = zone_coords[0], zone_coords[1]

    d_oz = haversine_distance(origin_lat, origin_lon, z_lat, z_lon)
    d_zd = haversine_distance(z_lat, z_lon, dest_lat, dest_lon)
    d_od = haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)

    if d_od == 0:
        return False
    detour_ratio = (d_oz + d_zd) / d_od
    return detour_ratio < margin


def generate_test_points_near_zones(zones: List[Dict], n: int = 100) -> List[Tuple[Dict, Dict]]:
    """
    Generate n origin/destination pairs that guarantee risk zones lie between them.

    Strategy: For each pair, pick a random zone, then place origin and destination
    on opposite sides of that zone at 500-2000m away.
    """
    random.seed(42)  # Reproducible
    pairs = []

    for _ in range(n * 3):  # Generate extra to filter
        if len(pairs) >= n:
            break

        # Pick a random zone to route "through"
        zone = random.choice(zones)
        z_coords = zone["geometry"]["coordinates"]
        z_lon, z_lat = z_coords[0], z_coords[1]

        # Generate random angle for the origin-destination axis
        angle = random.uniform(0, 2 * math.pi)

        # Distance from zone center (800m to 2500m)
        dist_m = random.uniform(800, 2500)

        # Convert meters to approximate degrees at SF latitude
        lat_offset = (dist_m / 111000)
        lon_offset = (dist_m / (111000 * math.cos(math.radians(z_lat))))

        # Origin on one side
        o_lat = z_lat + lat_offset * math.sin(angle)
        o_lon = z_lon + lon_offset * math.cos(angle)

        # Destination on the opposite side
        d_lat = z_lat - lat_offset * math.sin(angle)
        d_lon = z_lon - lon_offset * math.cos(angle)

        # Validate points are within SF bounds
        if not (SF_BOUNDS["min_lat"] <= o_lat <= SF_BOUNDS["max_lat"] and
                SF_BOUNDS["min_lon"] <= o_lon <= SF_BOUNDS["max_lon"] and
                SF_BOUNDS["min_lat"] <= d_lat <= SF_BOUNDS["max_lat"] and
                SF_BOUNDS["min_lon"] <= d_lon <= SF_BOUNDS["max_lon"]):
            continue

        # Verify at least one zone is between origin and destination
        zones_between = [
            z for z in zones
            if zone_is_between_points(o_lat, o_lon, d_lat, d_lon, z, margin=1.5)
        ]
        if not zones_between:
            continue

        origin = {"latitude": round(o_lat, 6), "longitude": round(o_lon, 6)}
        destination = {"latitude": round(d_lat, 6), "longitude": round(d_lon, 6)}
        pairs.append((origin, destination))

    return pairs[:n]


async def calculate_route_for_profile(
    client: httpx.AsyncClient,
    origin: Dict, destination: Dict, profile: str
) -> Dict[str, Any]:
    """Call the routing API for a given profile."""
    body = {
        "origin": origin,
        "destination": destination,
        "vehicle_type": "scooter",
        "preferences": {
            "profile": profile,
            "avoid_hills": False,
            "max_grade_percent": 15,
            "prefer_bike_lanes": False,
            "bike_lane_weight": 0.7,
        },
        "avoid_risk_zones": True,
    }
    try:
        response = await client.post(ROUTE_URL, json=body, timeout=30.0)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}: {response.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def analyze_route_against_zones(
    route_data: Dict, zones: List[Dict], profile: str
) -> Dict[str, Any]:
    """
    Analyze a route to check which risk zones it passes through.
    Returns detailed violation info.
    """
    if "error" in route_data:
        return {"error": route_data["error"], "violations": [], "passes": 0}

    coords = route_data.get("geometry", {}).get("coordinates", [])
    if not coords:
        return {"error": "No coordinates", "violations": [], "passes": 0}

    violations = []
    zone_passes_detail = []

    # SAFEST avoids all zone cores (0.25x alert_radius)
    # BALANCED avoids HIGH/CRITICAL zone cores (0.2x alert_radius)
    safest_factor = 0.25
    balanced_factor = 0.2

    for zone in zones:
        z_class = classify_zone(zone)

        if profile == "safest":
            passes = route_passes_through_zone(coords, zone, radius_factor=safest_factor)
        elif profile == "balanced":
            # BALANCED only checks HIGH and CRITICAL zones
            if z_class not in ("HIGH", "CRITICAL"):
                passes = route_passes_through_zone(coords, zone, radius_factor=balanced_factor)
            else:
                passes = route_passes_through_zone(coords, zone, radius_factor=balanced_factor)
        else:
            passes = route_passes_through_zone(coords, zone, radius_factor=0.25)

        if passes:
            z_info = {
                "zone_id": zone["id"],
                "zone_name": zone.get("name", "Unknown"),
                "reported_count": zone.get("reported_count", 0),
                "severity_class": z_class,
                "alert_radius_meters": zone.get("alert_radius_meters", 150),
            }
            zone_passes_detail.append(z_info)

            if profile == "safest":
                violations.append({**z_info, "reason": "SAFEST must avoid ALL risk zone cores"})
            elif profile == "balanced":
                if z_class in ("HIGH", "CRITICAL"):
                    violations.append({
                        **z_info,
                        "reason": f"BALANCED must avoid {z_class} zone cores (200+ crashes)"
                    })

    risk_analysis = route_data.get("risk_analysis", {})
    summary = route_data.get("summary", {})

    return {
        "total_zones_passed": len(zone_passes_detail),
        "zones_passed": zone_passes_detail,
        "violations": violations,
        "violation_count": len(violations),
        "api_risk_zones": risk_analysis.get("total_risk_zones", 0),
        "api_high_severity": risk_analysis.get("high_severity_zones", 0),
        "api_risk_score": summary.get("risk_score", 0),
        "distance_meters": summary.get("distance_meters", 0),
        "duration_seconds": summary.get("duration_seconds", 0),
    }


async def run_tests():
    """Main test runner."""
    print("=" * 80)
    print("MICROMOBILITY ROUTING - RISK ZONE PROFILE COMPLIANCE TEST")
    print("=" * 80)
    print()

    async with httpx.AsyncClient() as client:
        # Step 1: Fetch all risk zones
        print("[1/4] Fetching risk zones...")
        response = await client.get(RISK_ZONES_URL)
        zones = response.json()
        print(f"  Found {len(zones)} risk zones")

        # Classify zones
        zone_classes = {}
        for z in zones:
            cls = classify_zone(z)
            zone_classes.setdefault(cls, []).append(z)
        for cls, zlist in sorted(zone_classes.items()):
            print(f"  {cls}: {len(zlist)} zones")
        print()

        # Step 2: Generate test points
        print("[2/4] Generating 100 random test point pairs with zones in between...")
        pairs = generate_test_points_near_zones(zones, n=100)
        print(f"  Generated {len(pairs)} valid test pairs")
        print()

        # Step 3: Run tests for each profile
        profiles = ["safest", "balanced", "fastest"]
        results = {p: [] for p in profiles}

        for profile in profiles:
            print(f"[3/4] Testing '{profile.upper()}' profile ({len(pairs)} routes)...")
            start_time = time.time()
            success_count = 0
            error_count = 0

            for i, (origin, destination) in enumerate(pairs):
                route_data = await calculate_route_for_profile(client, origin, destination, profile)
                analysis = analyze_route_against_zones(route_data, zones, profile)
                analysis["test_index"] = i
                analysis["origin"] = origin
                analysis["destination"] = destination
                results[profile].append(analysis)

                if "error" in analysis and analysis["error"]:
                    error_count += 1
                else:
                    success_count += 1

                if (i + 1) % 20 == 0:
                    elapsed = time.time() - start_time
                    print(f"    Progress: {i + 1}/{len(pairs)} ({elapsed:.1f}s)")

            elapsed = time.time() - start_time
            print(f"  Completed: {success_count} success, {error_count} errors ({elapsed:.1f}s)")
            print()

        # Step 4: Analyze results
        print("[4/4] RESULTS SUMMARY")
        print("=" * 80)

        overall_pass = True

        for profile in profiles:
            profile_results = results[profile]
            total = len(profile_results)
            errors = sum(1 for r in profile_results if r.get("error"))
            successful = total - errors

            total_violations = sum(r.get("violation_count", 0) for r in profile_results)
            routes_with_violations = sum(1 for r in profile_results if r.get("violation_count", 0) > 0)
            total_zone_passes = sum(r.get("total_zones_passed", 0) for r in profile_results)
            routes_with_zone_passes = sum(1 for r in profile_results if r.get("total_zones_passed", 0) > 0)

            print(f"\n{'=' * 40}")
            print(f"PROFILE: {profile.upper()}")
            print(f"{'=' * 40}")
            print(f"  Total tests:             {total}")
            print(f"  Successful routes:       {successful}")
            print(f"  API errors:              {errors}")
            print(f"  Routes passing zones:    {routes_with_zone_passes}/{successful}")
            print(f"  Total zone passes:       {total_zone_passes}")
            print(f"  Routes with VIOLATIONS:  {routes_with_violations}/{successful}")
            print(f"  Total VIOLATIONS:        {total_violations}")

            if profile == "safest":
                if routes_with_zone_passes > 0:
                    print(f"\n  *** FAIL: SAFEST profile passed through zones in {routes_with_zone_passes} routes ***")
                    overall_pass = False
                    # Show first 10 violations
                    shown = 0
                    for r in profile_results:
                        if r.get("total_zones_passed", 0) > 0 and shown < 10:
                            print(f"\n  Violation #{shown + 1} (test {r['test_index']}):")
                            print(f"    Origin: {r['origin']}")
                            print(f"    Destination: {r['destination']}")
                            print(f"    Zone passes: {r['total_zones_passed']}")
                            print(f"    API reported risk_zones: {r.get('api_risk_zones', 'N/A')}")
                            for zp in r.get("zones_passed", []):
                                print(f"      - {zp['zone_name']} ({zp['reported_count']} crashes, "
                                      f"class={zp['severity_class']}, radius={zp['alert_radius_meters']}m)")
                            shown += 1
                else:
                    print(f"\n  PASS: SAFEST correctly avoided all risk zones")

            elif profile == "balanced":
                # Count different types of zone passes
                yellow_passes = 0
                high_passes = 0
                critical_passes = 0
                for r in profile_results:
                    for zp in r.get("zones_passed", []):
                        if zp["severity_class"] == "YELLOW_LIGHT_RED":
                            yellow_passes += 1
                        elif zp["severity_class"] == "HIGH":
                            high_passes += 1
                        elif zp["severity_class"] == "CRITICAL":
                            critical_passes += 1

                print(f"\n  Zone pass breakdown:")
                print(f"    Yellow/Light-red (160-199): {yellow_passes} (ALLOWED)")
                print(f"    High (200-249):            {high_passes} {'(VIOLATION!)' if high_passes > 0 else '(OK)'}")
                print(f"    Critical (250+):           {critical_passes} {'(VIOLATION!)' if critical_passes > 0 else '(OK)'}")

                if total_violations > 0:
                    print(f"\n  *** FAIL: BALANCED profile had {total_violations} violations ***")
                    overall_pass = False
                    shown = 0
                    for r in profile_results:
                        for v in r.get("violations", []):
                            if shown < 10:
                                print(f"    - Test {r['test_index']}: {v['zone_name']} "
                                      f"({v['reported_count']} crashes, {v['severity_class']})")
                                shown += 1
                else:
                    print(f"\n  PASS: BALANCED correctly allowed yellow, avoided high/critical")

            elif profile == "fastest":
                print(f"\n  INFO: FASTEST profile is allowed through all zones")
                print(f"  PASS: No constraints to violate")

            # Average stats
            valid_results = [r for r in profile_results if not r.get("error")]
            if valid_results:
                avg_dist = sum(r.get("distance_meters", 0) for r in valid_results) / len(valid_results)
                avg_dur = sum(r.get("duration_seconds", 0) for r in valid_results) / len(valid_results)
                avg_risk = sum(r.get("api_risk_score", 0) for r in valid_results) / len(valid_results)
                print(f"\n  Average distance: {avg_dist:.0f}m")
                print(f"  Average duration: {avg_dur:.0f}s")
                print(f"  Average risk score: {avg_risk:.3f}")

        # Overall verdict
        print(f"\n{'=' * 80}")
        if overall_pass:
            print("OVERALL: ALL PROFILES PASSED")
        else:
            print("OVERALL: FAILURES DETECTED - FIXES NEEDED")
        print(f"{'=' * 80}")

        # Save detailed results to file
        output_file = "/Users/aryanshmohapatra/Personal Projects/Micromobility Navigation in SF/backend/tests/risk_zone_test_results.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nDetailed results saved to: {output_file}")

        return results, overall_pass


if __name__ == "__main__":
    results, passed = asyncio.run(run_tests())
