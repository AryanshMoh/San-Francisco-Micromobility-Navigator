import { useRouteStore } from '../../store/routeStore';
import { useNavigationStore } from '../../store/navigationStore';
import RouteSummary from './RouteSummary';
import RouteOptions from './RouteOptions';

export default function RoutePanel() {
  const { route, alternatives, clearRoute } = useRouteStore();
  const { startNavigation } = useNavigationStore();

  if (!route) return null;

  const handleStartNavigation = () => {
    // In a real app, this would create a navigation session via API
    const sessionId = crypto.randomUUID();
    const sessionToken = crypto.randomUUID();
    startNavigation(sessionId, sessionToken, route);
  };

  return (
    <div className="route-panel">
      <div className="p-4">
        {/* Handle for dragging */}
        <div className="flex justify-center mb-2">
          <div className="w-12 h-1 bg-gray-300 rounded-full" />
        </div>

        {/* Route Summary */}
        <RouteSummary summary={route.summary} />

        {/* Route Options (preferences) */}
        <RouteOptions />

        {/* Risk warnings */}
        {route.riskAnalysis.totalRiskZones > 0 && (
          <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
            <div className="flex items-start gap-2">
              <span className="text-xl">⚠️</span>
              <div>
                <p className="text-sm font-medium text-yellow-800">
                  {route.riskAnalysis.totalRiskZones} risk zone(s) on route
                </p>
                {route.riskAnalysis.highSeverityZones > 0 && (
                  <p className="text-xs text-yellow-700 mt-1">
                    Including {route.riskAnalysis.highSeverityZones} high-severity zone(s)
                  </p>
                )}
                <p className="text-xs text-yellow-600 mt-1">
                  You will receive audio warnings when approaching these areas
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Alternative routes */}
        {alternatives.length > 1 && (
          <div className="mt-4">
            <h3 className="text-sm font-medium text-gray-600 mb-2">
              Alternative Routes
            </h3>
            <div className="space-y-2">
              {alternatives.map((alt, index) => (
                <button
                  key={alt.routeId}
                  className={`w-full p-3 rounded-lg border text-left transition-colors ${
                    alt.routeId === route.routeId
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => useRouteStore.getState().setRoute(alt)}
                >
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">
                      {index === 0 ? 'Safest' : index === 1 ? 'Fastest' : 'Balanced'}
                    </span>
                    <span className="text-sm text-gray-600">
                      {formatDuration(alt.summary.durationSeconds)}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {formatDistance(alt.summary.distanceMeters)} •{' '}
                    {alt.summary.bikeLanePercentage.toFixed(0)}% bike lanes
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="mt-4 flex gap-3">
          <button
            onClick={clearRoute}
            className="flex-1 py-3 rounded-lg font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleStartNavigation}
            className="flex-1 py-3 rounded-lg font-medium bg-primary-600 text-white hover:bg-primary-700 transition-colors"
          >
            Start Navigation
          </button>
        </div>
      </div>
    </div>
  );
}

function formatDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

function formatDistance(meters: number): string {
  if (meters < 1000) {
    return `${Math.round(meters)} m`;
  }
  const km = meters / 1000;
  return `${km.toFixed(1)} km`;
}
