export type HazardSeverity = 'low' | 'medium' | 'high' | 'critical';

export type HazardType =
  | 'pothole'
  | 'dangerous_intersection'
  | 'blind_turn'
  | 'poor_pavement'
  | 'construction'
  | 'high_traffic'
  | 'steep_grade'
  | 'narrow_passage'
  | 'door_zone'
  | 'trolley_tracks'
  | 'cable_car_tracks'
  | 'muni_conflict'
  | 'pedestrian_heavy'
  | 'other';

export type DataSource =
  | 'sf_311'
  | 'osm'
  | 'user_report'
  | 'municipal'
  | 'automated'
  | 'manual_survey';

export interface GeoJSONPoint {
  type: 'Point';
  coordinates: number[];
}

export interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

export type RiskZoneGeometry = GeoJSONPoint | GeoJSONPolygon;

export interface RiskZone {
  id: string;
  geometry: RiskZoneGeometry;
  hazardType: HazardType;
  severity: HazardSeverity;
  name?: string;
  description?: string;
  alertRadiusMeters: number;
  alertMessage?: string;
  isPermanent: boolean;
  source: DataSource;
  confidenceScore: number;
  reportedCount: number;
  isActive: boolean;
  createdAt: string;
  expiresAt?: string;
}

export interface NearbyRiskZone {
  riskZone: RiskZone;
  distanceMeters: number;
}

// Lucide icon names for hazard types
export type HazardIconName =
  | 'circle-dot'
  | 'alert-triangle'
  | 'rotate-ccw'
  | 'square-dashed'
  | 'construction'
  | 'car'
  | 'mountain'
  | 'move-horizontal'
  | 'door-open'
  | 'train-track'
  | 'cable-car'
  | 'bus'
  | 'users'
  | 'zap';

// Hazard type display info
export const HAZARD_TYPE_INFO: Record<HazardType, { label: string; iconName: HazardIconName }> = {
  pothole: { label: 'Pothole', iconName: 'circle-dot' },
  dangerous_intersection: { label: 'Dangerous Intersection', iconName: 'alert-triangle' },
  blind_turn: { label: 'Blind Turn', iconName: 'rotate-ccw' },
  poor_pavement: { label: 'Poor Pavement', iconName: 'square-dashed' },
  construction: { label: 'Construction', iconName: 'construction' },
  high_traffic: { label: 'High Traffic', iconName: 'car' },
  steep_grade: { label: 'Steep Hill', iconName: 'mountain' },
  narrow_passage: { label: 'Narrow Passage', iconName: 'move-horizontal' },
  door_zone: { label: 'Door Zone', iconName: 'door-open' },
  trolley_tracks: { label: 'Trolley Tracks', iconName: 'train-track' },
  cable_car_tracks: { label: 'Cable Car Tracks', iconName: 'cable-car' },
  muni_conflict: { label: 'Muni Conflict', iconName: 'bus' },
  pedestrian_heavy: { label: 'Heavy Pedestrians', iconName: 'users' },
  other: { label: 'Other Hazard', iconName: 'zap' },
};

export const SEVERITY_COLORS: Record<HazardSeverity, string> = {
  low: '#fbbf24',
  medium: '#f97316',
  high: '#ef4444',
  critical: '#7f1d1d',
};
