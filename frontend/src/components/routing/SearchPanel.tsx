import { useState, useCallback } from 'react';
import { useRouteStore } from '../../store/routeStore';
import { useMapStore } from '../../store/mapStore';
import { useRouting } from '../../hooks/useRouting';
import { useGeolocation } from '../../hooks/useGeolocation';
import { isWithinSFBounds } from '../map/MapContainer';
import {
  Navigation,
  MapPin,
  ArrowUpDown,
  Crosshair,
  Loader2,
  AlertTriangle,
  X,
} from 'lucide-react';

export default function SearchPanel() {
  const [originText, setOriginText] = useState('');
  const [destText, setDestText] = useState('');
  const [gpsError, setGpsError] = useState<string | null>(null);

  const {
    origin,
    destination,
    setOrigin,
    setDestination,
    swapLocations,
    clearRoute,
  } = useRouteStore();

  const { flyTo } = useMapStore();
  const { calculate, isCalculating, error } = useRouting();
  const { getCurrentPosition } = useGeolocation();

  const handleUseCurrentLocation = useCallback(async () => {
    setGpsError(null);
    try {
      const position = await getCurrentPosition();

      if (!isWithinSFBounds(position.latitude, position.longitude)) {
        setGpsError('GPS cannot be used outside of San Francisco');
        return;
      }

      setOrigin(position);
      setOriginText('Current Location');
      flyTo(position.longitude, position.latitude);
    } catch (err) {
      console.error('Failed to get current location:', err);
      setGpsError('Failed to get current location');
    }
  }, [getCurrentPosition, setOrigin, flyTo]);

  const handleSwap = useCallback(() => {
    swapLocations();
    const tempText = originText;
    setOriginText(destText);
    setDestText(tempText);
  }, [swapLocations, originText, destText]);

  const handleClear = useCallback(() => {
    setOrigin(null);
    setDestination(null);
    clearRoute();
    setOriginText('');
    setDestText('');
    setGpsError(null);
  }, [setOrigin, setDestination, clearRoute]);

  const canCalculate = origin && destination && !isCalculating;

  return (
    <div className="search-panel">
      <div className="bg-white rounded-2xl shadow-medium p-5">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-accent-50 rounded-lg flex items-center justify-center">
              <Navigation className="w-4 h-4 text-accent-600" />
            </div>
            <h1 className="text-base font-semibold text-slate-900 tracking-tight">
              SF Micromobility
            </h1>
          </div>
          {(origin || destination) && (
            <button
              onClick={handleClear}
              className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              aria-label="Clear route"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Location Inputs */}
        <div className="space-y-3">
          {/* Origin input */}
          <div className="relative">
            <div className="absolute left-3.5 top-1/2 -translate-y-1/2">
              <div className="w-2.5 h-2.5 bg-accent-500 rounded-full ring-2 ring-accent-100" />
            </div>
            <input
              type="text"
              placeholder="Starting point"
              value={originText || (origin ? `${origin.latitude.toFixed(4)}, ${origin.longitude.toFixed(4)}` : '')}
              onChange={(e) => setOriginText(e.target.value)}
              className="w-full h-11 pl-9 pr-20 text-sm text-slate-800 placeholder:text-slate-400 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-500 transition-all"
            />
            <button
              onClick={handleUseCurrentLocation}
              className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-accent-600 hover:text-accent-700 hover:bg-accent-50 rounded-lg transition-colors"
            >
              <Crosshair className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">GPS</span>
            </button>
          </div>

          {/* GPS Error message */}
          {gpsError && (
            <div className="flex items-center gap-2 px-3 py-2 bg-caution-50 border border-caution-200 rounded-lg">
              <AlertTriangle className="w-4 h-4 text-caution-500 flex-shrink-0" />
              <span className="text-xs text-caution-600">{gpsError}</span>
            </div>
          )}

          {/* Swap button */}
          <div className="flex justify-center -my-1">
            <button
              onClick={handleSwap}
              className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full transition-colors"
              title="Swap origin and destination"
            >
              <ArrowUpDown className="w-4 h-4" />
            </button>
          </div>

          {/* Destination input */}
          <div className="relative">
            <div className="absolute left-3.5 top-1/2 -translate-y-1/2">
              <MapPin className="w-4 h-4 text-alert-500" />
            </div>
            <input
              type="text"
              placeholder="Destination"
              value={destText || (destination ? `${destination.latitude.toFixed(4)}, ${destination.longitude.toFixed(4)}` : '')}
              onChange={(e) => setDestText(e.target.value)}
              className="w-full h-11 pl-9 pr-4 text-sm text-slate-800 placeholder:text-slate-400 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent-500/20 focus:border-accent-500 transition-all"
            />
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="mt-4 flex items-center gap-2 px-3 py-2.5 bg-alert-50 border border-alert-200 rounded-lg">
            <AlertTriangle className="w-4 h-4 text-alert-500 flex-shrink-0" />
            <span className="text-xs text-alert-600">{error}</span>
          </div>
        )}

        {/* Calculate button */}
        <button
          onClick={calculate}
          disabled={!canCalculate}
          className={`mt-5 w-full h-12 rounded-xl font-medium text-sm transition-all duration-200 ${
            canCalculate
              ? 'bg-slate-900 text-white hover:bg-slate-800 active:scale-[0.98]'
              : 'bg-slate-100 text-slate-400 cursor-not-allowed'
          }`}
        >
          {isCalculating ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Calculating</span>
            </span>
          ) : (
            'Get Route'
          )}
        </button>

        {/* Quick tip */}
        <p className="mt-4 text-xs text-slate-400 text-center leading-relaxed">
          Tap on the map to set your start and end points
        </p>
      </div>
    </div>
  );
}
