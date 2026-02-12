import { useEffect, useState, useMemo, useCallback } from 'react';
import { Source, Layer } from 'react-map-gl';
import type { LayerProps } from 'react-map-gl';
import type { Expression } from 'mapbox-gl';

// ============================================================================
// SF Open Data - SFMTA Bikeway Network (Complete Dataset)
// https://data.sfgov.org/Transportation/MTA-Bike-Network-Linear-Features/ygmz-vaxd
// Updated quarterly - includes 5,440 total segments
// ============================================================================

const SF_BIKE_LANES_API = 'https://data.sfgov.org/resource/ygmz-vaxd.geojson?$limit=10000';

// Cache for bike lane data (module-level for SWR-like dedup)
let bikeLaneCache: { data: BikeNetworkGeoJSON | null; timestamp: number } = {
  data: null,
  timestamp: 0,
};
const CACHE_DURATION = 30 * 60 * 1000; // 30 minutes

// ============================================================================
// Bike Lane Classifications
// Only show REAL protected infrastructure, NOT sharrows/bike routes
// ============================================================================

// CLASS I:  Off-street bike paths (fully separated trails)
// CLASS II: Painted bike lanes on streets (dedicated lane markings)
// CLASS IV: Protected/separated bikeways (physical barriers)
// EXCLUDED: CLASS III "Bike Routes" - just sharrows on regular roads

const REAL_BIKE_LANE_TYPES = new Set(['CLASS I', 'CLASS II', 'CLASS IV']);

// ============================================================================
// Types
// ============================================================================

interface BikeNetworkFeature {
  type: 'Feature';
  geometry: {
    type: 'LineString' | 'MultiLineString';
    coordinates: number[][] | number[][][];
  };
  properties: {
    facility_t?: string;     // CLASS I, II, III, IV
    symbology?: string;      // BIKE PATH, BIKE LANE, SEPARATED BIKEWAY, etc.
    streetname?: string;
    install_yr?: string;
    buffered?: string;       // YES/NO - has buffer zone
    raised?: string;         // YES/NO - raised lane
    contraflow?: string;     // YES/NO - contraflow lane
    greenwave?: string;      // YES/NO - has green wave timing
  };
}

interface BikeNetworkGeoJSON {
  type: 'FeatureCollection';
  features: BikeNetworkFeature[];
}

// ============================================================================
// Mapbox Layer Styles - Hoisted for Performance
// Premium visual hierarchy inspired by cartographic design
// ============================================================================

// Color palette - refined greens with hierarchy
const COLORS = {
  // Class I - Off-street paths (safest, most prominent)
  pathCore: '#059669',       // Emerald 600 - rich, deep
  pathGlow: '#34d399',       // Emerald 400 - bright glow

  // Class IV - Protected bikeways (very safe, prominent)
  protectedCore: '#10b981',  // Emerald 500 - vibrant
  protectedGlow: '#6ee7b7',  // Emerald 300 - soft glow

  // Class II - Painted lanes (moderate protection)
  laneCore: '#22c55e',       // Green 500 - standard
  laneGlow: '#86efac',       // Green 300 - subtle
};

// Dynamic color expression based on facility type
const lineColorExpression: Expression = [
  'match',
  ['get', 'facility_t'],
  'CLASS I', COLORS.pathCore,
  'CLASS IV', COLORS.protectedCore,
  'CLASS II', COLORS.laneCore,
  COLORS.laneCore, // fallback
];

const glowColorExpression: Expression = [
  'match',
  ['get', 'facility_t'],
  'CLASS I', COLORS.pathGlow,
  'CLASS IV', COLORS.protectedGlow,
  'CLASS II', COLORS.laneGlow,
  COLORS.laneGlow, // fallback
];

// Line width by facility type (protected lanes more prominent)
const lineWidthExpression: Expression = [
  'interpolate',
  ['linear'],
  ['zoom'],
  11, ['match', ['get', 'facility_t'], 'CLASS I', 2.5, 'CLASS IV', 2, 1.5],
  14, ['match', ['get', 'facility_t'], 'CLASS I', 4, 'CLASS IV', 3.5, 3],
  17, ['match', ['get', 'facility_t'], 'CLASS I', 6, 'CLASS IV', 5, 4],
];

// Glow width (outer halo for visibility)
const glowWidthExpression: Expression = [
  'interpolate',
  ['linear'],
  ['zoom'],
  11, ['match', ['get', 'facility_t'], 'CLASS I', 6, 'CLASS IV', 5, 4],
  14, ['match', ['get', 'facility_t'], 'CLASS I', 10, 'CLASS IV', 9, 7],
  17, ['match', ['get', 'facility_t'], 'CLASS I', 14, 'CLASS IV', 12, 10],
];

// Opacity by zoom level (fade in gracefully)
const opacityExpression: Expression = [
  'interpolate',
  ['linear'],
  ['zoom'],
  10, 0,
  11, 0.6,
  13, 0.85,
  16, 1,
];

const glowOpacityExpression: Expression = [
  'interpolate',
  ['linear'],
  ['zoom'],
  10, 0,
  11, 0.15,
  13, 0.25,
  16, 0.35,
];

// ============================================================================
// Layer Configurations
// ============================================================================

const bikeLanesGlowLayer: LayerProps = {
  id: 'bike-lanes-glow',
  type: 'line',
  paint: {
    'line-color': glowColorExpression,
    'line-width': glowWidthExpression,
    'line-opacity': glowOpacityExpression,
    'line-blur': 3,
  },
  layout: {
    'line-join': 'round',
    'line-cap': 'round',
  },
};

const bikeLanesCoreLayer: LayerProps = {
  id: 'bike-lanes-core',
  type: 'line',
  paint: {
    'line-color': lineColorExpression,
    'line-width': lineWidthExpression,
    'line-opacity': opacityExpression,
  },
  layout: {
    'line-join': 'round',
    'line-cap': 'round',
  },
};

// Dashed pattern for Class II (painted) lanes at high zoom
const bikeLanesPatternLayer: LayerProps = {
  id: 'bike-lanes-pattern',
  type: 'line',
  filter: ['==', ['get', 'facility_t'], 'CLASS II'],
  minzoom: 15,
  paint: {
    'line-color': '#ffffff',
    'line-width': 1.5,
    'line-opacity': 0.4,
    'line-dasharray': [4, 6],
  },
  layout: {
    'line-join': 'round',
    'line-cap': 'round',
  },
};

// ============================================================================
// Component
// ============================================================================

export default function BikeLanesLayer() {
  const [geoJsonData, setGeoJsonData] = useState<BikeNetworkGeoJSON | null>(null);
  const [loading, setLoading] = useState(true);
  const [_stats, setStats] = useState<{
    total: number;
    classI: number;
    classII: number;
    classIV: number;
    excluded: number;
  } | null>(null);

  // Fetch bike lanes with caching
  const fetchBikeLanes = useCallback(async () => {
    // Check cache first
    const now = Date.now();
    if (bikeLaneCache.data && now - bikeLaneCache.timestamp < CACHE_DURATION) {
      setGeoJsonData(bikeLaneCache.data);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(SF_BIKE_LANES_API);

      if (!response.ok) {
        throw new Error(`Failed to fetch bike lanes: ${response.status}`);
      }

      const data = await response.json();

      // Filter and categorize
      let classI = 0;
      let classII = 0;
      let classIV = 0;
      let excluded = 0;

      const filteredFeatures = data.features.filter((f: BikeNetworkFeature) => {
        const facilityType = f.properties?.facility_t;

        if (!facilityType || !REAL_BIKE_LANE_TYPES.has(facilityType)) {
          excluded++;
          return false;
        }

        // Count by type
        switch (facilityType) {
          case 'CLASS I':
            classI++;
            break;
          case 'CLASS II':
            classII++;
            break;
          case 'CLASS IV':
            classIV++;
            break;
        }

        return true;
      });

      const filteredData: BikeNetworkGeoJSON = {
        type: 'FeatureCollection',
        features: filteredFeatures,
      };

      // Update cache
      bikeLaneCache = { data: filteredData, timestamp: now };

      setStats({
        total: filteredFeatures.length,
        classI,
        classII,
        classIV,
        excluded,
      });

      console.log(
        `🚴 Loaded ${filteredFeatures.length} bike lanes from SFMTA:\n` +
        `   • Class I (paths): ${classI}\n` +
        `   • Class II (lanes): ${classII}\n` +
        `   • Class IV (protected): ${classIV}\n` +
        `   • Excluded (sharrows): ${excluded}`
      );

      setGeoJsonData(filteredData);
    } catch (err) {
      console.error('Error fetching bike lanes:', err);
      // Use fallback data
      const fallback = getFallbackBikeLanes();
      setGeoJsonData(fallback);
      setStats({
        total: fallback.features.length,
        classI: 2,
        classII: 3,
        classIV: 3,
        excluded: 0,
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBikeLanes();
  }, [fetchBikeLanes]);

  // Memoize the source data to prevent re-renders
  const sourceData = useMemo(() => geoJsonData, [geoJsonData]);

  if (loading || !sourceData) {
    return null;
  }

  return (
    <Source id="bike-lanes" type="geojson" data={sourceData}>
      {/* Outer glow for visibility */}
      <Layer {...bikeLanesGlowLayer} />

      {/* Core line */}
      <Layer {...bikeLanesCoreLayer} />

      {/* Dashed pattern for Class II at high zoom */}
      <Layer {...bikeLanesPatternLayer} />
    </Source>
  );
}

// ============================================================================
// Fallback Data - Major SF Bike Routes
// Used when API is unavailable
// ============================================================================

function getFallbackBikeLanes(): BikeNetworkGeoJSON {
  return {
    type: 'FeatureCollection',
    features: [
      // Market Street - CLASS IV Protected Bikeway
      {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [-122.4194, 37.7749],
            [-122.4144, 37.7791],
            [-122.4094, 37.7833],
            [-122.4044, 37.7875],
            [-122.3994, 37.7917],
          ],
        },
        properties: {
          facility_t: 'CLASS IV',
          symbology: 'SEPARATED BIKEWAY',
          streetname: 'MARKET ST',
        },
      },
      // The Embarcadero - CLASS I Bike Path
      {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [-122.3880, 37.7955],
            [-122.3910, 37.7945],
            [-122.3940, 37.7925],
            [-122.3960, 37.7900],
            [-122.3955, 37.7870],
            [-122.3940, 37.7840],
            [-122.3910, 37.7810],
            [-122.3890, 37.7785],
          ],
        },
        properties: {
          facility_t: 'CLASS I',
          symbology: 'BIKE PATH',
          streetname: 'THE EMBARCADERO',
        },
      },
      // Valencia Street - CLASS IV Protected
      {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [-122.4218, 37.7700],
            [-122.4215, 37.7660],
            [-122.4212, 37.7620],
            [-122.4208, 37.7580],
            [-122.4205, 37.7540],
            [-122.4200, 37.7500],
          ],
        },
        properties: {
          facility_t: 'CLASS IV',
          symbology: 'SEPARATED BIKEWAY',
          streetname: 'VALENCIA ST',
        },
      },
      // Polk Street - CLASS II Bike Lane
      {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [-122.4200, 37.7850],
            [-122.4208, 37.7890],
            [-122.4215, 37.7930],
            [-122.4222, 37.7970],
            [-122.4230, 37.8010],
          ],
        },
        properties: {
          facility_t: 'CLASS II',
          symbology: 'BIKE LANE',
          streetname: 'POLK ST',
        },
      },
      // Golden Gate Park / Panhandle - CLASS I Path
      {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [-122.4370, 37.7730],
            [-122.4420, 37.7722],
            [-122.4470, 37.7715],
            [-122.4520, 37.7708],
            [-122.4570, 37.7702],
            [-122.4620, 37.7696],
            [-122.4670, 37.7690],
            [-122.4720, 37.7686],
            [-122.4770, 37.7685],
          ],
        },
        properties: {
          facility_t: 'CLASS I',
          symbology: 'BIKE PATH',
          streetname: 'PANHANDLE',
        },
      },
      // Folsom Street - CLASS II
      {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [-122.3950, 37.7880],
            [-122.4000, 37.7865],
            [-122.4050, 37.7850],
            [-122.4100, 37.7835],
            [-122.4150, 37.7820],
            [-122.4200, 37.7805],
            [-122.4250, 37.7790],
          ],
        },
        properties: {
          facility_t: 'CLASS II',
          symbology: 'BIKE LANE',
          streetname: 'FOLSOM ST',
        },
      },
      // Howard Street - CLASS IV Protected
      {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [-122.3970, 37.7875],
            [-122.4020, 37.7858],
            [-122.4070, 37.7842],
            [-122.4120, 37.7825],
            [-122.4170, 37.7808],
          ],
        },
        properties: {
          facility_t: 'CLASS IV',
          symbology: 'SEPARATED BIKEWAY',
          streetname: 'HOWARD ST',
        },
      },
      // 2nd Street - CLASS IV
      {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [-122.4000, 37.7920],
            [-122.3997, 37.7880],
            [-122.3993, 37.7840],
            [-122.3990, 37.7800],
            [-122.3987, 37.7760],
          ],
        },
        properties: {
          facility_t: 'CLASS IV',
          symbology: 'SEPARATED BIKEWAY',
          streetname: '2ND ST',
        },
      },
    ],
  };
}
