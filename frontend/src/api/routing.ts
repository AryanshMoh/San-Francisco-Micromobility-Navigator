import { apiRequest } from './index';
import { Route, RouteRequest, RouteComparison } from '../types';

export async function calculateRoute(request: RouteRequest): Promise<Route> {
  // Convert camelCase to snake_case for API
  const apiRequest_body = {
    origin: request.origin,
    destination: request.destination,
    vehicle_type: request.vehicleType,
    preferences: {
      profile: request.preferences.profile,
      avoid_hills: request.preferences.avoidHills,
      max_grade_percent: request.preferences.maxGradePercent,
      prefer_bike_lanes: request.preferences.preferBikeLanes,
      bike_lane_weight: request.preferences.bikeLaneWeight,
    },
    avoid_risk_zones: request.avoidRiskZones,
    departure_time: request.departureTime,
  };

  const response = await apiRequest<{
    route_id: string;
    geometry: { type: string; coordinates: number[][] };
    summary: {
      distance_meters: number;
      duration_seconds: number;
      elevation_gain_meters: number;
      elevation_loss_meters: number;
      max_grade_percent: number;
      bike_lane_percentage: number;
      risk_score: number;
    };
    legs: unknown[];
    risk_analysis: {
      total_risk_zones: number;
      high_severity_zones: number;
      risk_zone_ids: string[];
    };
    warnings: unknown[];
  }>('/api/v1/routes/calculate', {
    method: 'POST',
    body: JSON.stringify(apiRequest_body),
  });

  // Convert snake_case response to camelCase
  return {
    routeId: response.route_id,
    geometry: response.geometry as Route['geometry'],
    summary: {
      distanceMeters: response.summary.distance_meters,
      durationSeconds: response.summary.duration_seconds,
      elevationGainMeters: response.summary.elevation_gain_meters,
      elevationLossMeters: response.summary.elevation_loss_meters,
      maxGradePercent: response.summary.max_grade_percent,
      bikeLanePercentage: response.summary.bike_lane_percentage,
      riskScore: response.summary.risk_score,
    },
    legs: [], // TODO: Parse legs properly
    riskAnalysis: {
      totalRiskZones: response.risk_analysis.total_risk_zones,
      highSeverityZones: response.risk_analysis.high_severity_zones,
      riskZoneIds: response.risk_analysis.risk_zone_ids,
    },
    warnings: [],
  };
}

export async function getAlternativeRoutes(
  request: RouteRequest
): Promise<{ routes: Route[]; comparison: RouteComparison }> {
  const apiRequestBody = {
    origin: request.origin,
    destination: request.destination,
    vehicle_type: request.vehicleType,
    preferences: {
      profile: request.preferences.profile,
      avoid_hills: request.preferences.avoidHills,
      max_grade_percent: request.preferences.maxGradePercent,
      prefer_bike_lanes: request.preferences.preferBikeLanes,
      bike_lane_weight: request.preferences.bikeLaneWeight,
    },
    avoid_risk_zones: request.avoidRiskZones,
  };

  const response = await apiRequest<{
    routes: unknown[];
    comparison: {
      fastest_index: number;
      safest_index: number;
      recommended_index: number;
    };
  }>('/api/v1/routes/alternatives', {
    method: 'POST',
    body: JSON.stringify(apiRequestBody),
  });

  return {
    routes: response.routes as Route[], // TODO: Parse properly
    comparison: {
      fastestIndex: response.comparison.fastest_index,
      safestIndex: response.comparison.safest_index,
      recommendedIndex: response.comparison.recommended_index,
    },
  };
}
