import { useEffect, useRef, useCallback } from 'react';
import { useNavigationStore } from '../store/navigationStore';
import { Coordinate, Maneuver } from '../types/route';
import { RiskZone } from '../types/riskZone';
import { ApproachingRiskZone } from '../types/navigation';
import { isWithinSFBounds } from '../components/map/MapContainer';

// Haversine formula for distance calculation
function calculateDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371000; // Earth's radius in meters
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// Find the closest point on a route to the current location
function findClosestPointOnRoute(
  location: Coordinate,
  routeCoords: number[][]
): { index: number; distance: number; point: Coordinate } {
  let minDistance = Infinity;
  let closestIndex = 0;
  let closestPoint: Coordinate = { latitude: 0, longitude: 0 };

  for (let i = 0; i < routeCoords.length; i++) {
    const [lon, lat] = routeCoords[i];
    const dist = calculateDistance(location.latitude, location.longitude, lat, lon);

    if (dist < minDistance) {
      minDistance = dist;
      closestIndex = i;
      closestPoint = { latitude: lat, longitude: lon };
    }
  }

  return { index: closestIndex, distance: minDistance, point: closestPoint };
}

// Calculate remaining distance from a point on the route
function calculateRemainingDistance(
  routeCoords: number[][],
  fromIndex: number
): number {
  let distance = 0;
  for (let i = fromIndex; i < routeCoords.length - 1; i++) {
    const [lon1, lat1] = routeCoords[i];
    const [lon2, lat2] = routeCoords[i + 1];
    distance += calculateDistance(lat1, lon1, lat2, lon2);
  }
  return distance;
}

// Find the next maneuver based on current position
function findNextManeuver(
  location: Coordinate,
  maneuvers: Maneuver[]
): { maneuver: Maneuver | null; distance: number } {
  for (const maneuver of maneuvers) {
    const dist = calculateDistance(
      location.latitude,
      location.longitude,
      maneuver.location.latitude,
      maneuver.location.longitude
    );

    // Return the first maneuver that's still ahead (more than 10m away)
    if (dist > 10) {
      return { maneuver, distance: dist };
    }
  }

  // All maneuvers passed, return the last one (arrival)
  const lastManeuver = maneuvers[maneuvers.length - 1];
  if (lastManeuver) {
    const dist = calculateDistance(
      location.latitude,
      location.longitude,
      lastManeuver.location.latitude,
      lastManeuver.location.longitude
    );
    return { maneuver: lastManeuver, distance: dist };
  }

  return { maneuver: null, distance: 0 };
}

// Check for approaching risk zones
async function checkApproachingRiskZones(
  location: Coordinate,
  _routeCoords: number[][],
  _currentIndex: number,
  speedMps: number
): Promise<ApproachingRiskZone[]> {
  // Fetch nearby risk zones from API
  const lookAheadMeters = 500; // Look 500m ahead
  const bbox = calculateBoundingBox(location, lookAheadMeters);

  try {
    const response = await fetch(
      `/api/v1/risk-zones?min_lat=${bbox.minLat}&max_lat=${bbox.maxLat}&min_lng=${bbox.minLng}&max_lng=${bbox.maxLng}`
    );

    if (!response.ok) return [];

    const data = await response.json();
    const zones: RiskZone[] = data.risk_zones || [];

    // Calculate distance to each zone along the route
    const approaching: ApproachingRiskZone[] = [];

    for (const zone of zones) {
      if (zone.geometry.type !== 'Point') continue;

      const [zoneLon, zoneLat] = zone.geometry.coordinates;
      const distanceToZone = calculateDistance(
        location.latitude,
        location.longitude,
        zoneLat,
        zoneLon
      );

      // Only include zones within alert radius + 200m
      if (distanceToZone < zone.alertRadiusMeters + 200) {
        const etaSeconds = speedMps > 0 ? distanceToZone / speedMps : 0;

        approaching.push({
          riskZone: zone,
          distanceMeters: distanceToZone,
          etaSeconds,
          alertTriggered: distanceToZone < zone.alertRadiusMeters,
        });
      }
    }

    // Sort by distance
    return approaching.sort((a, b) => a.distanceMeters - b.distanceMeters);
  } catch {
    return [];
  }
}

function calculateBoundingBox(center: Coordinate, radiusMeters: number) {
  const latDelta = radiusMeters / 111000; // ~111km per degree of latitude
  const lonDelta = radiusMeters / (111000 * Math.cos((center.latitude * Math.PI) / 180));

  return {
    minLat: center.latitude - latDelta,
    maxLat: center.latitude + latDelta,
    minLng: center.longitude - lonDelta,
    maxLng: center.longitude + lonDelta,
  };
}

export function useNavigationTracking() {
  const {
    isActive,
    route,
    updateLocation,
    updateNavigationState,
    addApproachingZone,
    clearApproachingZone,
  } = useNavigationStore();

  const watchIdRef = useRef<number | null>(null);
  const lastRiskCheckRef = useRef<number>(0);
  const isOutsideSFRef = useRef<boolean>(false);
  const simulationActiveRef = useRef<boolean>(false);

  const handlePositionUpdate = useCallback(
    async (position: GeolocationPosition) => {
      if (!route) return;

      const rawLatitude = position.coords.latitude;
      const rawLongitude = position.coords.longitude;

      // If GPS location is outside SF bounds, use the route's starting point
      // This allows users outside SF to still test the navigation
      let location: Coordinate;
      if (!isWithinSFBounds(rawLatitude, rawLongitude)) {
        isOutsideSFRef.current = true;
        const [startLon, startLat] = route.geometry.coordinates[0];
        location = {
          latitude: startLat,
          longitude: startLon,
        };
      } else {
        isOutsideSFRef.current = false;
        location = {
          latitude: rawLatitude,
          longitude: rawLongitude,
        };
      }

      const heading = position.coords.heading ?? undefined;
      const speed = position.coords.speed ?? undefined;

      // Update current location in store
      updateLocation(location, heading, speed);

      // Find position on route
      const routeCoords = route.geometry.coordinates;
      const closest = findClosestPointOnRoute(location, routeCoords);

      // Check if off-route (more than 30 meters from route)
      const isOnRoute = closest.distance < 30;

      // Calculate remaining distance
      const distanceRemaining = isOnRoute
        ? calculateRemainingDistance(routeCoords, closest.index)
        : route.summary.distanceMeters;

      // Estimate remaining duration based on current speed or average
      const avgSpeed = speed && speed > 0 ? speed : 4.5; // Default 4.5 m/s (~10 mph)
      const durationRemaining = distanceRemaining / avgSpeed;

      // Find next maneuver
      const allManeuvers = route.legs.flatMap((leg) => leg.maneuvers);
      const { maneuver: nextManeuver, distance: distanceToManeuver } =
        findNextManeuver(location, allManeuvers);

      // Update navigation state
      updateNavigationState({
        onRoute: isOnRoute,
        distanceRemainingMeters: distanceRemaining,
        durationRemainingSeconds: durationRemaining,
        nextManeuver,
        distanceToManeuverMeters: distanceToManeuver,
      });

      // Check for risk zones periodically (every 5 seconds)
      const now = Date.now();
      if (now - lastRiskCheckRef.current > 5000) {
        lastRiskCheckRef.current = now;

        const approaching = await checkApproachingRiskZones(
          location,
          routeCoords,
          closest.index,
          speed || 4.5
        );

        // Update approaching zones
        // Clear zones that are no longer approaching
        const approachingIds = new Set(approaching.map((z) => z.riskZone.id));
        const currentZones = useNavigationStore.getState().approachingRiskZones;

        currentZones.forEach((zone) => {
          if (!approachingIds.has(zone.riskZone.id)) {
            clearApproachingZone(zone.riskZone.id);
          }
        });

        // Add/update approaching zones
        approaching.forEach((zone) => {
          addApproachingZone(zone);
        });
      }
    },
    [route, updateLocation, updateNavigationState, addApproachingZone, clearApproachingZone]
  );

  const handlePositionError = useCallback((error: GeolocationPositionError) => {
    console.warn('Navigation tracking error:', error.message);
  }, []);

  // Start/stop geolocation tracking based on navigation state
  useEffect(() => {
    if (!isActive || !route) {
      // Stop tracking
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
      return;
    }

    // Start tracking with high accuracy
    watchIdRef.current = navigator.geolocation.watchPosition(
      handlePositionUpdate,
      handlePositionError,
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );

    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
    };
  }, [isActive, route, handlePositionUpdate, handlePositionError]);

  // Simulate location updates for development/testing
  useEffect(() => {
    if (!isActive || !route) return;

    // If no real GPS, simulate movement along route for testing
    let simulationInterval: NodeJS.Timeout | null = null;
    let currentIndex = 0;

    const startSimulation = () => {
      // Stop GPS watch when using simulation (for users outside SF)
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
      simulationActiveRef.current = true;
      const coords = route.geometry.coordinates;

      simulationInterval = setInterval(() => {
        if (currentIndex >= coords.length - 1) {
          currentIndex = 0; // Loop for testing
        }

        const [lon, lat] = coords[currentIndex];
        const nextIndex = Math.min(currentIndex + 1, coords.length - 1);
        const [nextLon, nextLat] = coords[nextIndex];

        // Calculate heading
        const heading =
          (Math.atan2(nextLon - lon, nextLat - lat) * 180) / Math.PI;

        // Simulate position
        const mockCoords = {
          latitude: lat,
          longitude: lon,
          accuracy: 5,
          altitude: null,
          altitudeAccuracy: null,
          heading,
          speed: 4.5, // ~10 mph
          toJSON() {
            return this;
          },
        };
        const mockPosition = {
          coords: mockCoords,
          timestamp: Date.now(),
        } as GeolocationPosition;

        handlePositionUpdate(mockPosition);
        currentIndex++;
      }, 1000);
    };

    // Start simulation if no GPS after 3 seconds OR if GPS is outside SF bounds
    const timeoutId = setTimeout(() => {
      const state = useNavigationStore.getState();
      if (!state.currentLocation || isOutsideSFRef.current) {
        console.log('No SF GPS detected, starting route simulation');
        startSimulation();
      }
    }, 3000);

    return () => {
      clearTimeout(timeoutId);
      if (simulationInterval) {
        clearInterval(simulationInterval);
      }
      simulationActiveRef.current = false;
      isOutsideSFRef.current = false;
    };
  }, [isActive, route, handlePositionUpdate]);
}
