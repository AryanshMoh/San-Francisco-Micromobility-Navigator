import { Layer, Source } from 'react-map-gl';
import { Route } from '../../types';

interface RouteLayerProps {
  route: Route;
  isAlternative?: boolean;
}

export default function RouteLayer({ route, isAlternative = false }: RouteLayerProps) {
  // Convert route geometry to GeoJSON format for Mapbox
  const geojson = {
    type: 'Feature' as const,
    properties: {},
    geometry: route.geometry,
  };

  const lineColor = isAlternative ? '#9ca3af' : '#16a34a'; // Gray for alternatives, green for main
  const lineWidth = isAlternative ? 4 : 6;
  const lineOpacity = isAlternative ? 0.6 : 1;

  return (
    <Source id={`route-${route.routeId}`} type="geojson" data={geojson}>
      {/* Route outline (border) */}
      <Layer
        id={`route-outline-${route.routeId}`}
        type="line"
        paint={{
          'line-color': '#ffffff',
          'line-width': lineWidth + 2,
          'line-opacity': lineOpacity,
        }}
        layout={{
          'line-join': 'round',
          'line-cap': 'round',
        }}
      />

      {/* Main route line */}
      <Layer
        id={`route-line-${route.routeId}`}
        type="line"
        paint={{
          'line-color': lineColor,
          'line-width': lineWidth,
          'line-opacity': lineOpacity,
        }}
        layout={{
          'line-join': 'round',
          'line-cap': 'round',
        }}
      />

      {/* Route direction arrows */}
      <Layer
        id={`route-arrows-${route.routeId}`}
        type="symbol"
        layout={{
          'symbol-placement': 'line',
          'symbol-spacing': 100,
          'icon-image': 'arrow',
          'icon-size': 0.5,
          'icon-allow-overlap': true,
        }}
      />
    </Source>
  );
}
