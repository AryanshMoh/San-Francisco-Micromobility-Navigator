import { useCallback, useRef } from 'react';
import Map, { MapRef, NavigationControl, GeolocateControl } from 'react-map-gl';
import { useMapStore } from '../../store/mapStore';
import { useRouteStore } from '../../store/routeStore';
import RouteLayer from './RouteLayer';
import UserLocationMarker from './UserLocationMarker';
import MapControls from './MapControls';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || '';

// San Francisco bounds
const SF_BOUNDS: [[number, number], [number, number]] = [
  [-122.52, 37.70], // Southwest
  [-122.35, 37.82], // Northeast
];

export default function MapContainer() {
  const mapRef = useRef<MapRef>(null);
  const { viewState, setViewState, showBikeLanes } = useMapStore();
  const { route, setOrigin, setDestination, origin, destination } = useRouteStore();

  // Show fallback if no Mapbox token
  if (!MAPBOX_TOKEN || MAPBOX_TOKEN === 'YOUR_MAPBOX_TOKEN_HERE') {
    return (
      <div className="h-full w-full bg-gray-100 flex items-center justify-center">
        <div className="bg-white p-8 rounded-xl shadow-lg max-w-md text-center">
          <div className="text-6xl mb-4">🗺️</div>
          <h2 className="text-xl font-bold text-gray-800 mb-2">Mapbox Token Required</h2>
          <p className="text-gray-600 mb-4">
            To display the map, add your Mapbox token to:
          </p>
          <code className="block bg-gray-100 p-2 rounded text-sm mb-4">
            frontend/.env
          </code>
          <p className="text-gray-500 text-sm">
            Get a free token at{' '}
            <a href="https://mapbox.com" target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">
              mapbox.com
            </a>
          </p>
        </div>
      </div>
    );
  }

  const handleMove = useCallback(
    (evt: { viewState: typeof viewState }) => {
      setViewState(evt.viewState);
    },
    [setViewState]
  );

  const handleClick = useCallback(
    (evt: { lngLat: { lng: number; lat: number } }) => {
      const { lng, lat } = evt.lngLat;
      const coord = { latitude: lat, longitude: lng };

      // If no origin set, set origin; otherwise set destination
      if (!origin) {
        setOrigin(coord);
      } else if (!destination) {
        setDestination(coord);
      } else {
        // Both set, update destination
        setDestination(coord);
      }
    },
    [origin, destination, setOrigin, setDestination]
  );

  // Map style with bike lanes if available
  const mapStyle = showBikeLanes
    ? 'mapbox://styles/mapbox/streets-v12'
    : 'mapbox://styles/mapbox/light-v11';

  return (
    <div className="h-full w-full">
      <Map
        ref={mapRef}
        {...viewState}
        onMove={handleMove}
        onClick={handleClick}
        mapboxAccessToken={MAPBOX_TOKEN}
        mapStyle={mapStyle}
        maxBounds={SF_BOUNDS}
        style={{ width: '100%', height: '100%' }}
        attributionControl={false}
      >
        {/* Navigation controls */}
        <NavigationControl position="bottom-right" />
        <GeolocateControl
          position="bottom-right"
          trackUserLocation
          showUserHeading
          positionOptions={{ enableHighAccuracy: true }}
        />

        {/* Route layer */}
        {route && <RouteLayer route={route} />}

        {/* User-placed markers for origin/destination */}
        {origin && (
          <UserLocationMarker
            longitude={origin.longitude}
            latitude={origin.latitude}
            type="origin"
          />
        )}
        {destination && (
          <UserLocationMarker
            longitude={destination.longitude}
            latitude={destination.latitude}
            type="destination"
          />
        )}
      </Map>

      {/* Layer toggle controls */}
      <MapControls />
    </div>
  );
}
