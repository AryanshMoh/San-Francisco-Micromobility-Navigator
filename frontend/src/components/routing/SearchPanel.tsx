import { useState, useCallback } from 'react';
import { useRouteStore } from '../../store/routeStore';
import { useMapStore } from '../../store/mapStore';
import { useRouting } from '../../hooks/useRouting';
import { useGeolocation } from '../../hooks/useGeolocation';

export default function SearchPanel() {
  const [originText, setOriginText] = useState('');
  const [destText, setDestText] = useState('');

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
    try {
      const position = await getCurrentPosition();
      setOrigin(position);
      setOriginText('Current Location');
      flyTo(position.longitude, position.latitude);
    } catch (err) {
      console.error('Failed to get current location:', err);
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
  }, [setOrigin, setDestination, clearRoute]);

  const canCalculate = origin && destination && !isCalculating;

  return (
    <div className="search-panel">
      <div className="bg-white rounded-xl shadow-lg p-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-lg font-semibold text-gray-800">SF Micromobility</h1>
          {(origin || destination) && (
            <button
              onClick={handleClear}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Clear
            </button>
          )}
        </div>

        {/* Origin input */}
        <div className="space-y-3">
          <div className="relative">
            <div className="absolute left-3 top-1/2 -translate-y-1/2">
              <div className="w-3 h-3 bg-green-500 rounded-full" />
            </div>
            <input
              type="text"
              placeholder="Starting point"
              value={originText || (origin ? `${origin.latitude.toFixed(4)}, ${origin.longitude.toFixed(4)}` : '')}
              onChange={(e) => setOriginText(e.target.value)}
              className="input pl-8 pr-20"
            />
            <button
              onClick={handleUseCurrentLocation}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-primary-600 hover:text-primary-700 font-medium"
            >
              Use GPS
            </button>
          </div>

          {/* Swap button */}
          <div className="flex justify-center">
            <button
              onClick={handleSwap}
              className="p-1 hover:bg-gray-100 rounded-full transition-colors"
              title="Swap origin and destination"
            >
              <svg
                className="w-5 h-5 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"
                />
              </svg>
            </button>
          </div>

          {/* Destination input */}
          <div className="relative">
            <div className="absolute left-3 top-1/2 -translate-y-1/2">
              <div className="w-3 h-3 bg-red-500 rounded-full" />
            </div>
            <input
              type="text"
              placeholder="Destination"
              value={destText || (destination ? `${destination.latitude.toFixed(4)}, ${destination.longitude.toFixed(4)}` : '')}
              onChange={(e) => setDestText(e.target.value)}
              className="input pl-8"
            />
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="mt-3 p-2 bg-red-50 text-red-600 text-sm rounded-lg">
            {error}
          </div>
        )}

        {/* Calculate button */}
        <button
          onClick={calculate}
          disabled={!canCalculate}
          className={`mt-4 w-full py-3 rounded-lg font-medium transition-colors ${
            canCalculate
              ? 'bg-primary-600 text-white hover:bg-primary-700'
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
          }`}
        >
          {isCalculating ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Calculating...
            </span>
          ) : (
            'Get Route'
          )}
        </button>

        {/* Quick tip */}
        <p className="mt-3 text-xs text-gray-400 text-center">
          Tap on the map to set origin and destination points
        </p>
      </div>
    </div>
  );
}
