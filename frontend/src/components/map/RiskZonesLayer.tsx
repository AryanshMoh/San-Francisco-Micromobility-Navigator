import { useEffect, useState } from 'react';
import { Source, Layer, Popup } from 'react-map-gl';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Risk zone thresholds - no green, start with yellow
const THRESHOLD_MIN = 140;
const THRESHOLD_YELLOW_MAX = 179;
// 180-229 is light red, 230+ is dark red

interface RiskZoneFeature {
  type: 'Feature';
  geometry: {
    type: 'Point';
    coordinates: [number, number];
  };
  properties: {
    id: string;
    severity: 'MEDIUM' | 'HIGH';
    name: string;
    description: string;
    reported_count: number;
    alert_radius_meters: number;
    hazard_type: string;
  };
}

interface RiskZonesGeoJSON {
  type: 'FeatureCollection';
  features: RiskZoneFeature[];
}

interface PopupInfo {
  longitude: number;
  latitude: number;
  properties: RiskZoneFeature['properties'];
}

/**
 * Get color based on accident count with gradient effect
 * Yellow: 140-179, Light Red: 180-229, Dark Red: 230+
 */
function getGradientColor(count: number): string {
  if (count <= THRESHOLD_YELLOW_MAX) {
    // Yellow range: 140-179 → #fef08a to #eab308
    const intensity = (count - THRESHOLD_MIN) / (THRESHOLD_YELLOW_MAX - THRESHOLD_MIN);
    const r = Math.round(254 - intensity * (254 - 234));
    const g = Math.round(240 - intensity * (240 - 179));
    const b = Math.round(138 - intensity * (138 - 8));
    return `rgb(${r}, ${g}, ${b})`;
  } else if (count <= 229) {
    // Light Red range: 180-229 → #fca5a5 to #dc2626
    const intensity = (count - 180) / (229 - 180);
    const r = Math.round(252 - intensity * (252 - 220));
    const g = Math.round(165 - intensity * (165 - 38));
    const b = Math.round(165 - intensity * (165 - 38));
    return `rgb(${r}, ${g}, ${b})`;
  } else {
    // Dark Red range: 230+ → #b91c1c to #7f1d1d
    const maxRed = 300;
    const intensity = Math.min(1, (count - 230) / (maxRed - 230));
    const r = Math.round(185 - intensity * (185 - 127));
    const g = Math.round(28 - intensity * (28 - 29));
    const b = Math.round(28 - intensity * (28 - 29));
    return `rgb(${r}, ${g}, ${b})`;
  }
}

// [rerender-memo] Hoist static Mapbox expressions outside the component
// to avoid recreating on every render
const COLOR_EXPRESSION: unknown[] = [
  'interpolate',
  ['linear'],
  ['get', 'reported_count'],
  // Yellow: 140-179
  140, '#fef08a',  // Light yellow
  179, '#eab308',  // Dark yellow/amber
  // Light Red: 180-229
  180, '#fca5a5',  // Light red
  229, '#dc2626',  // Red
  // Dark Red: 230+
  230, '#b91c1c',  // Dark red
  300, '#7f1d1d',  // Maroon
];

const METERS_PER_PIXEL_Z0 = 123675;

// Core danger zone: 0.25x of alert_radius (matches routing avoidance and risk zone counting)
// This is the actual "danger core" that routes avoid and that counts toward "X risk zones on route"
// Full alert radius expression - used for the faint "awareness zone" halo
const FULL_RADIUS_EXPRESSION: unknown[] = [
  'interpolate',
  ['exponential', 2],
  ['zoom'],
  10, ['*', ['get', 'alert_radius_meters'], 1024 / METERS_PER_PIXEL_Z0],
  11, ['*', ['get', 'alert_radius_meters'], 2048 / METERS_PER_PIXEL_Z0],
  12, ['*', ['get', 'alert_radius_meters'], 4096 / METERS_PER_PIXEL_Z0],
  13, ['*', ['get', 'alert_radius_meters'], 8192 / METERS_PER_PIXEL_Z0],
  14, ['*', ['get', 'alert_radius_meters'], 16384 / METERS_PER_PIXEL_Z0],
  15, ['*', ['get', 'alert_radius_meters'], 32768 / METERS_PER_PIXEL_Z0],
  16, ['*', ['get', 'alert_radius_meters'], 65536 / METERS_PER_PIXEL_Z0],
  17, ['*', ['get', 'alert_radius_meters'], 131072 / METERS_PER_PIXEL_Z0],
  18, ['*', ['get', 'alert_radius_meters'], 262144 / METERS_PER_PIXEL_Z0],
];

// [rendering-hoist-jsx] Hoist static paint objects outside component
// Halo uses full radius to show awareness zone
const HALO_RADIUS: unknown[] = ['+', FULL_RADIUS_EXPRESSION, 4];

// Module-level cache for risk zones fetch (client-swr-dedup pattern)
let cachedRiskZones: RiskZonesGeoJSON | null = null;
let fetchPromise: Promise<RiskZonesGeoJSON> | null = null;

async function fetchRiskZonesData(): Promise<RiskZonesGeoJSON> {
  if (cachedRiskZones) return cachedRiskZones;
  if (fetchPromise) return fetchPromise;

  fetchPromise = (async () => {
    const bbox = '-122.52,37.70,-122.35,37.82';
    const response = await fetch(`${API_BASE}/api/v1/risk-zones?bbox=${bbox}`);
    if (!response.ok) throw new Error('Failed to fetch risk zones');
    const zones = await response.json();

    const geojson: RiskZonesGeoJSON = {
      type: 'FeatureCollection',
      features: zones.map((zone: any) => ({
        type: 'Feature',
        geometry: zone.geometry,
        properties: {
          id: zone.id,
          severity: zone.severity,
          name: zone.name || '',
          description: zone.description || '',
          reported_count: zone.reported_count || zone.reportedCount || 0,
          alert_radius_meters: zone.alert_radius_meters || zone.alertRadiusMeters || 150,
          hazard_type: zone.hazard_type || zone.hazardType || 'UNKNOWN',
        },
      })),
    };

    cachedRiskZones = geojson;
    fetchPromise = null;
    return geojson;
  })();

  return fetchPromise;
}

export default function RiskZonesLayer() {
  const [riskZones, setRiskZones] = useState<RiskZonesGeoJSON | null>(cachedRiskZones);
  const [loading, setLoading] = useState(!cachedRiskZones);
  const [popupInfo, setPopupInfo] = useState<PopupInfo | null>(null);

  useEffect(() => {
    if (cachedRiskZones) {
      setRiskZones(cachedRiskZones);
      setLoading(false);
      return;
    }

    let cancelled = false;
    fetchRiskZonesData()
      .then((data) => { if (!cancelled) { setRiskZones(data); setLoading(false); } })
      .catch(() => { if (!cancelled) { setRiskZones({ type: 'FeatureCollection', features: [] }); setLoading(false); } });
    return () => { cancelled = true; };
  }, []);

  if (loading || !riskZones) {
    return null;
  }

  return (
    <>
      {/* Non-clustered source - all zones shown individually at all zoom levels */}
      <Source
        id="risk-zones"
        type="geojson"
        data={riskZones}
      >
        {/* Outer glow/halo for visibility */}
        <Layer
          id="risk-zones-halo"
          type="circle"
          paint={{
            'circle-radius': HALO_RADIUS as any,
            'circle-color': COLOR_EXPRESSION as any,
            'circle-opacity': 0.2,
            'circle-blur': 0.5,
          }}
        />

        {/* Main circle fill - represents full alert radius */}
        <Layer
          id="risk-zones-fill"
          type="circle"
          paint={{
            'circle-radius': FULL_RADIUS_EXPRESSION as any,
            'circle-color': COLOR_EXPRESSION as any,
            'circle-opacity': 0.5,
          }}
        />

        {/* Circle outline */}
        <Layer
          id="risk-zones-outline"
          type="circle"
          paint={{
            'circle-radius': FULL_RADIUS_EXPRESSION as any,
            'circle-color': 'transparent',
            'circle-stroke-width': 2,
            'circle-stroke-color': COLOR_EXPRESSION as any,
            'circle-stroke-opacity': 0.8,
          }}
        />
      </Source>

      {/* Popup for clicked zone */}
      {popupInfo && (
        <Popup
          longitude={popupInfo.longitude}
          latitude={popupInfo.latitude}
          anchor="bottom"
          onClose={() => setPopupInfo(null)}
          closeButton
          closeOnClick={false}
        >
          <div className="p-2 min-w-[200px]">
            <div className="flex items-center gap-2 mb-2">
              <div
                className="w-4 h-4 rounded-full"
                style={{ backgroundColor: getGradientColor(popupInfo.properties.reported_count) }}
              />
              <span className="text-sm font-semibold text-slate-800">
                {popupInfo.properties.reported_count} Crashes
              </span>
            </div>
            <p className="text-xs text-slate-600 mb-1">
              {popupInfo.properties.name}
            </p>
            <p className="text-xs text-slate-500">
              {popupInfo.properties.description}
            </p>
          </div>
        </Popup>
      )}
    </>
  );
}
