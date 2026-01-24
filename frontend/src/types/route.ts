export interface Coordinate {
  latitude: number;
  longitude: number;
}

export type VehicleType = 'scooter' | 'bike' | 'ebike';

export type RouteProfile = 'safest' | 'fastest' | 'balanced' | 'scenic';

export interface RoutePreferences {
  profile: RouteProfile;
  avoidHills: boolean;
  maxGradePercent: number;
  preferBikeLanes: boolean;
  bikeLaneWeight: number;
}

export interface RouteRequest {
  origin: Coordinate;
  destination: Coordinate;
  vehicleType: VehicleType;
  preferences: RoutePreferences;
  avoidRiskZones: boolean;
  departureTime?: string;
}

export type ManeuverType =
  | 'depart'
  | 'arrive'
  | 'turn_left'
  | 'turn_right'
  | 'slight_left'
  | 'slight_right'
  | 'straight'
  | 'u_turn'
  | 'merge'
  | 'fork'
  | 'roundabout';

export type BikeLaneStatus = 'entering' | 'leaving' | 'continuing' | 'none';

export interface ManeuverAlert {
  type: string;
  message: string;
  severity: string;
}

export interface Maneuver {
  type: ManeuverType;
  instruction: string;
  verbalInstruction: string;
  location: Coordinate;
  distanceMeters: number;
  streetName?: string;
  bikeLaneStatus: BikeLaneStatus;
  alerts: ManeuverAlert[];
}

export interface GeoJSONLineString {
  type: 'LineString';
  coordinates: number[][];
}

export interface RouteLeg {
  geometry: GeoJSONLineString;
  distanceMeters: number;
  durationSeconds: number;
  maneuvers: Maneuver[];
}

export interface RouteSummary {
  distanceMeters: number;
  durationSeconds: number;
  elevationGainMeters: number;
  elevationLossMeters: number;
  maxGradePercent: number;
  bikeLanePercentage: number;
  riskScore: number;
}

export interface RouteRiskAnalysis {
  totalRiskZones: number;
  highSeverityZones: number;
  riskZoneIds: string[];
}

export interface RouteWarning {
  type: string;
  message: string;
  location?: Coordinate;
}

export interface Route {
  routeId: string;
  geometry: GeoJSONLineString;
  summary: RouteSummary;
  legs: RouteLeg[];
  riskAnalysis: RouteRiskAnalysis;
  warnings: RouteWarning[];
}

export interface RouteComparison {
  fastestIndex: number;
  safestIndex: number;
  recommendedIndex: number;
}
