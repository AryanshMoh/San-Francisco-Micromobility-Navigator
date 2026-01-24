import { Coordinate, Route, Maneuver } from './route';
import { RiskZone } from './riskZone';

export interface ApproachingRiskZone {
  riskZone: RiskZone;
  distanceMeters: number;
  etaSeconds: number;
  alertTriggered: boolean;
}

export interface NavigationState {
  sessionId: string;
  sessionToken: string;
  route: Route;
  currentLocation: Coordinate | null;
  heading: number | null;
  speedMps: number | null;
  onRoute: boolean;
  distanceRemainingMeters: number;
  durationRemainingSeconds: number;
  nextManeuver: Maneuver | null;
  distanceToManeuverMeters: number;
  approachingRiskZones: ApproachingRiskZone[];
}

export interface LocationUpdate {
  latitude: number;
  longitude: number;
  accuracyMeters?: number;
  heading?: number;
  speedMps?: number;
  timestamp: string;
}

export interface NavigationUpdate {
  onRoute: boolean;
  distanceRemainingMeters: number;
  durationRemainingSeconds: number;
  nextManeuver: Maneuver | null;
  distanceToManeuverMeters: number;
  approachingRiskZones: ApproachingRiskZone[];
  rerouteSuggested: boolean;
  suggestedRoute?: Route;
}

// WebSocket message types
export type WSClientMessageType = 'location_update' | 'acknowledge_alert';
export type WSServerMessageType = 'navigation_update' | 'risk_alert' | 'reroute_available' | 'off_route';

export interface WSClientMessage {
  type: WSClientMessageType;
  data: Record<string, unknown>;
}

export interface WSServerMessage {
  type: WSServerMessageType;
  data: Record<string, unknown>;
}
