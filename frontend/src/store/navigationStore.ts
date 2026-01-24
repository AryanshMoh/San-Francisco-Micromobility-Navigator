import { create } from 'zustand';
import { Coordinate, Route, Maneuver } from '../types/route';
import { RiskZone } from '../types/riskZone';
import { ApproachingRiskZone } from '../types/navigation';

interface NavigationStore {
  // Session state
  sessionId: string | null;
  sessionToken: string | null;
  route: Route | null;

  // Current state
  currentLocation: Coordinate | null;
  heading: number | null;
  speedMps: number | null;

  // Progress
  onRoute: boolean;
  distanceRemainingMeters: number;
  durationRemainingSeconds: number;
  nextManeuver: Maneuver | null;
  distanceToManeuverMeters: number;

  // Alerts
  approachingRiskZones: ApproachingRiskZone[];
  pendingAlerts: RiskZone[];

  // Status
  isActive: boolean;
  audioEnabled: boolean;
  rerouteCount: number;

  // Actions
  startNavigation: (sessionId: string, sessionToken: string, route: Route) => void;
  updateLocation: (location: Coordinate, heading?: number, speed?: number) => void;
  updateNavigationState: (update: Partial<NavigationStore>) => void;
  addApproachingZone: (zone: ApproachingRiskZone) => void;
  clearApproachingZone: (zoneId: string) => void;
  addPendingAlert: (zone: RiskZone) => void;
  clearPendingAlert: (zoneId: string) => void;
  toggleAudio: () => void;
  incrementRerouteCount: () => void;
  endNavigation: () => void;
}

export const useNavigationStore = create<NavigationStore>((set) => ({
  // Initial state
  sessionId: null,
  sessionToken: null,
  route: null,
  currentLocation: null,
  heading: null,
  speedMps: null,
  onRoute: true,
  distanceRemainingMeters: 0,
  durationRemainingSeconds: 0,
  nextManeuver: null,
  distanceToManeuverMeters: 0,
  approachingRiskZones: [],
  pendingAlerts: [],
  isActive: false,
  audioEnabled: true,
  rerouteCount: 0,

  startNavigation: (sessionId, sessionToken, route) =>
    set({
      sessionId,
      sessionToken,
      route,
      isActive: true,
      distanceRemainingMeters: route.summary.distanceMeters,
      durationRemainingSeconds: route.summary.durationSeconds,
      nextManeuver: route.legs[0]?.maneuvers[0] || null,
      onRoute: true,
      rerouteCount: 0,
    }),

  updateLocation: (location, heading, speed) =>
    set({
      currentLocation: location,
      heading: heading ?? null,
      speedMps: speed ?? null,
    }),

  updateNavigationState: (update) =>
    set((state) => ({
      ...state,
      ...update,
    })),

  addApproachingZone: (zone) =>
    set((state) => ({
      approachingRiskZones: [...state.approachingRiskZones.filter(z => z.riskZone.id !== zone.riskZone.id), zone],
    })),

  clearApproachingZone: (zoneId) =>
    set((state) => ({
      approachingRiskZones: state.approachingRiskZones.filter(z => z.riskZone.id !== zoneId),
    })),

  addPendingAlert: (zone) =>
    set((state) => ({
      pendingAlerts: state.pendingAlerts.some(z => z.id === zone.id)
        ? state.pendingAlerts
        : [...state.pendingAlerts, zone],
    })),

  clearPendingAlert: (zoneId) =>
    set((state) => ({
      pendingAlerts: state.pendingAlerts.filter(z => z.id !== zoneId),
    })),

  toggleAudio: () =>
    set((state) => ({
      audioEnabled: !state.audioEnabled,
    })),

  incrementRerouteCount: () =>
    set((state) => ({
      rerouteCount: state.rerouteCount + 1,
    })),

  endNavigation: () =>
    set({
      sessionId: null,
      sessionToken: null,
      route: null,
      currentLocation: null,
      heading: null,
      speedMps: null,
      onRoute: true,
      distanceRemainingMeters: 0,
      durationRemainingSeconds: 0,
      nextManeuver: null,
      distanceToManeuverMeters: 0,
      approachingRiskZones: [],
      pendingAlerts: [],
      isActive: false,
      rerouteCount: 0,
    }),
}));
