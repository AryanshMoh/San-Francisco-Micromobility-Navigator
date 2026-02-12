import { useCallback, useRef } from 'react';
import Map, { MapRef, NavigationControl, GeolocateControl } from 'react-map-gl';
import { useMapStore } from '../../store/mapStore';
import { useRouteStore } from '../../store/routeStore';
import { useNavigationStore } from '../../store/navigationStore';
import RouteLayer from './RouteLayer';
import UserLocationMarker from './UserLocationMarker';
import CurrentLocationMarker from './CurrentLocationMarker';
import MapControls from './MapControls';
import BikeLanesLayer from './BikeLanesLayer';
import RiskZonesLayer from './RiskZonesLayer';
import { Map as MapIcon, ExternalLink } from 'lucide-react';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || '';

// San Francisco bounds
const SF_BOUNDS = {
  minLng: -122.52,
  maxLng: -122.35,
  minLat: 37.70,
  maxLat: 37.82,
};

// Check if a coordinate is within SF bounds
export function isWithinSFBounds(lat: number, lng: number): boolean {
  return (
    lng >= SF_BOUNDS.minLng &&
    lng <= SF_BOUNDS.maxLng &&
    lat >= SF_BOUNDS.minLat &&
    lat <= SF_BOUNDS.maxLat
  );
}

export default function MapContainer() {
  const mapRef = useRef<MapRef>(null);
  // [rerender-derived-state] Granular selectors to minimize re-renders
  const viewState = useMapStore((s) => s.viewState);
  const setViewState = useMapStore((s) => s.setViewState);
  const showBikeLanes = useMapStore((s) => s.showBikeLanes);
  const showRiskZones = useMapStore((s) => s.showRiskZones);
  const route = useRouteStore((s) => s.route);
  const origin = useRouteStore((s) => s.origin);
  const destination = useRouteStore((s) => s.destination);
  const setOrigin = useRouteStore((s) => s.setOrigin);
  const setDestination = useRouteStore((s) => s.setDestination);
  const isNavigating = useNavigationStore((s) => s.isActive);
  const currentLocation = useNavigationStore((s) => s.currentLocation);
  const heading = useNavigationStore((s) => s.heading);
  const navRoute = useNavigationStore((s) => s.route);

  // Show fallback if no Mapbox token
  if (!MAPBOX_TOKEN || MAPBOX_TOKEN === 'YOUR_MAPBOX_TOKEN_HERE') {
    return (
      <div className="h-full w-full bg-slate-50 flex items-center justify-center p-6">
        <div className="bg-white p-8 rounded-2xl shadow-medium max-w-sm text-center">
          <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-5">
            <MapIcon className="w-8 h-8 text-slate-400" />
          </div>
          <h2 className="text-lg font-semibold text-slate-900 mb-2">
            Mapbox Token Required
          </h2>
          <p className="text-sm text-slate-500 mb-5 leading-relaxed">
            To display the map, add your Mapbox access token to the environment file.
          </p>
          <code className="block bg-slate-100 px-4 py-2.5 rounded-lg text-xs text-slate-600 font-mono mb-5">
            frontend/.env
          </code>
          <a
            href="https://mapbox.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-accent-600 hover:text-accent-700 font-medium"
          >
            Get a free token
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    );
  }

  // Constrain view to SF area
  const handleMove = useCallback(
    (evt: { viewState: typeof viewState }) => {
      const { longitude, latitude } = evt.viewState;

      // Soft boundary - push back if trying to leave SF area
      const constrainedLng = Math.max(SF_BOUNDS.minLng, Math.min(SF_BOUNDS.maxLng, longitude));
      const constrainedLat = Math.max(SF_BOUNDS.minLat, Math.min(SF_BOUNDS.maxLat, latitude));

      setViewState({
        ...evt.viewState,
        longitude: constrainedLng,
        latitude: constrainedLat,
      });
    },
    [setViewState]
  );

  // Handle map clicks for setting origin/destination
  const handleClick = useCallback(
    (evt: { lngLat: { lng: number; lat: number }; originalEvent: MouseEvent }) => {
      // Disable map clicks during navigation
      if (useNavigationStore.getState().isActive) {
        return;
      }

      // Check if click was on a marker
      const target = evt.originalEvent.target as HTMLElement;
      if (target.closest('.mapboxgl-marker')) {
        return;
      }

      const { lng, lat } = evt.lngLat;

      // Only allow clicks within SF bounds
      if (!isWithinSFBounds(lat, lng)) {
        return;
      }

      const coord = { latitude: lat, longitude: lng };

      // Get current state directly to avoid stale closure
      const currentOrigin = useRouteStore.getState().origin;
      const currentDestination = useRouteStore.getState().destination;

      if (!currentOrigin) {
        setOrigin(coord);
      } else if (!currentDestination) {
        setDestination(coord);
      } else {
        // Both set, update destination only
        setDestination(coord);
      }
    },
    [setOrigin, setDestination]
  );

  // Always use streets style for colorful map
  const mapStyle = 'mapbox://styles/mapbox/streets-v12';

  return (
    <div className="h-full w-full">
      <Map
        ref={mapRef}
        {...viewState}
        onMove={handleMove}
        onClick={handleClick}
        mapboxAccessToken={MAPBOX_TOKEN}
        mapStyle={mapStyle}
        minZoom={11}
        maxZoom={18}
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

        {/* Bike lanes layer */}
        {showBikeLanes && <BikeLanesLayer />}

        {/* Risk zones layer */}
        {showRiskZones && <RiskZonesLayer />}

        {/* [rendering-conditional-render] Use ternary to avoid rendering 0/false */}
        {(navRoute?.geometry?.coordinates?.length || route?.geometry?.coordinates?.length) ? (
          <RouteLayer route={(navRoute?.geometry?.coordinates?.length ? navRoute : route)!} />
        ) : null}

        {/* User-placed markers for origin/destination (hide during navigation) */}
        {!isNavigating && origin && (
          <UserLocationMarker
            longitude={origin.longitude}
            latitude={origin.latitude}
            type="origin"
          />
        )}
        {!isNavigating && destination && (
          <UserLocationMarker
            longitude={destination.longitude}
            latitude={destination.latitude}
            type="destination"
          />
        )}

        {/* Current location marker during navigation */}
        {isNavigating && currentLocation && (
          <CurrentLocationMarker
            longitude={currentLocation.longitude}
            latitude={currentLocation.latitude}
            heading={heading}
          />
        )}

        {/* Destination marker during navigation */}
        {isNavigating && navRoute && navRoute.geometry.coordinates.length > 0 && (
          <UserLocationMarker
            longitude={navRoute.geometry.coordinates[navRoute.geometry.coordinates.length - 1][0]}
            latitude={navRoute.geometry.coordinates[navRoute.geometry.coordinates.length - 1][1]}
            type="destination"
          />
        )}
      </Map>

      {/* Layer toggle controls - hide during navigation */}
      {!isNavigating && <MapControls />}
    </div>
  );
}
