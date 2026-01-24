import { apiRequest, buildQueryString } from './index';
import { RiskZone, NearbyRiskZone, HazardSeverity, HazardType } from '../types';

export async function getRiskZonesInArea(
  bbox: string,
  severity?: HazardSeverity,
  types?: HazardType[]
): Promise<RiskZone[]> {
  const params: Record<string, unknown> = { bbox };
  if (severity) params.severity = severity;
  if (types?.length) params.types = types.join(',');

  const query = buildQueryString(params);
  return apiRequest<RiskZone[]>(`/api/v1/risk-zones?${query}`);
}

export async function getRiskZonesNear(
  lat: number,
  lon: number,
  radius: number = 100
): Promise<{ zones: NearbyRiskZone[]; total: number }> {
  const query = buildQueryString({ lat, lon, radius });
  return apiRequest(`/api/v1/risk-zones/near?${query}`);
}

export async function getRiskZoneById(zoneId: string): Promise<RiskZone> {
  return apiRequest<RiskZone>(`/api/v1/risk-zones/${zoneId}`);
}
