// Route types
export type {
  Coordinate,
  VehicleType,
  RouteProfile,
  RoutePreferences,
  RouteRequest,
  ManeuverType,
  BikeLaneStatus,
  ManeuverAlert,
  Maneuver,
  GeoJSONLineString,
  RouteLeg,
  RouteSummary,
  RouteRiskAnalysis,
  RouteWarning,
  Route,
  RouteComparison,
} from './route';

// Risk zone types
export type {
  HazardSeverity,
  HazardType,
  DataSource,
  GeoJSONPoint,
  GeoJSONPolygon,
  RiskZoneGeometry,
  RiskZone,
  NearbyRiskZone,
} from './riskZone';

export { HAZARD_TYPE_INFO, SEVERITY_COLORS } from './riskZone';

// Navigation types
export type {
  ApproachingRiskZone,
  NavigationState,
  LocationUpdate,
  NavigationUpdate,
  WSClientMessageType,
  WSServerMessageType,
  WSClientMessage,
  WSServerMessage,
} from './navigation';
