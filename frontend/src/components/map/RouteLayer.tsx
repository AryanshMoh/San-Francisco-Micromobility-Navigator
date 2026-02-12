import { useMemo, memo } from 'react';
import { Layer, Source } from 'react-map-gl';
import { Route } from '../../types';

interface RouteLayerProps {
  route: Route;
  isAlternative?: boolean;
}

// [rerender-memo] Memoize to prevent re-renders from parent MapContainer
export default memo(function RouteLayer({ route, isAlternative = false }: RouteLayerProps) {
  // Don't render if route or geometry is invalid
  if (!route?.geometry?.coordinates?.length) {
    return null;
  }

  // [rerender-memo] Memoize GeoJSON to avoid new object reference on every render
  const geojson = useMemo(() => ({
    type: 'Feature' as const,
    properties: {},
    geometry: route.geometry,
  }), [route.geometry]);

  const lineColor = isAlternative ? '#9ca3af' : '#16a34a';
  const lineWidth = isAlternative ? 4 : 6;
  const lineOpacity = isAlternative ? 0.6 : 1;
  const sourceId = isAlternative ? 'route-alternative' : 'route-main';

  return (
    <Source id={sourceId} type="geojson" data={geojson}>
      {/* Route outline (border) */}
      <Layer
        id={`${sourceId}-outline`}
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
        id={`${sourceId}-line`}
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
        id={`${sourceId}-arrows`}
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
});
