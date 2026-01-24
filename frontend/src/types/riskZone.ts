import { Coordinate } from './route';

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

// Hazard type display names and colors
export const HAZARD_TYPE_INFO: Record<HazardType, { label: string; icon: string }> = {
  pothole: { label: 'Pothole', icon: '🕳️' },
  dangerous_intersection: { label: 'Dangerous Intersection', icon: '⚠️' },
  blind_turn: { label: 'Blind Turn', icon: '🔄' },
  poor_pavement: { label: 'Poor Pavement', icon: '🛤️' },
  construction: { label: 'Construction', icon: '🚧' },
  high_traffic: { label: 'High Traffic', icon: '🚗' },
  steep_grade: { label: 'Steep Hill', icon: '⛰️' },
  narrow_passage: { label: 'Narrow Passage', icon: '↔️' },
  door_zone: { label: 'Door Zone', icon: '🚪' },
  trolley_tracks: { label: 'Trolley Tracks', icon: '🚃' },
  cable_car_tracks: { label: 'Cable Car Tracks', icon: '🚡' },
  muni_conflict: { label: 'Muni Conflict', icon: '🚌' },
  pedestrian_heavy: { label: 'Heavy Pedestrians', icon: '🚶' },
  other: { label: 'Other Hazard', icon: '⚡' },
};

export const SEVERITY_COLORS: Record<HazardSeverity, string> = {
  low: '#fbbf24', // yellow
  medium: '#f97316', // orange
  high: '#ef4444', // red
  critical: '#7f1d1d', // dark red
};
