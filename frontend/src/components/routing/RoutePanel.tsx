import { useState, useCallback, useEffect, useRef } from 'react';
import { useRouteStore } from '../../store/routeStore';
import { useNavigationStore } from '../../store/navigationStore';
import RouteSummary from './RouteSummary';
import RouteOptions from './RouteOptions';
import SteepHillWarning from './SteepHillWarning';
import { AlertTriangle, Navigation, X, ChevronRight, ChevronDown, ChevronUp } from 'lucide-react';

const STEEP_HILL_THRESHOLD = 15; // 15% grade threshold

export default function RoutePanel() {
  // [rerender-derived-state] Use granular selectors to avoid re-renders
  // when unrelated store properties change
  const route = useRouteStore((s) => s.route);
  const alternatives = useRouteStore((s) => s.alternatives);
  const clearRoute = useRouteStore((s) => s.clearRoute);
  const startNavigation = useNavigationStore((s) => s.startNavigation);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showSteepHillWarning, setShowSteepHillWarning] = useState(false);

  // Track which route we've shown the warning for to avoid duplicate warnings
  const lastWarnedRouteId = useRef<string | null>(null);

  // Show steep hill warning when a new route with steep grade is generated
  useEffect(() => {
    if (!route) return;

    const maxGrade = route.summary?.maxGradePercent ?? 0;
    const routeId = route.routeId;

    // Only show warning for new routes with steep hills
    if (maxGrade > STEEP_HILL_THRESHOLD && routeId !== lastWarnedRouteId.current) {
      setShowSteepHillWarning(true);
      lastWarnedRouteId.current = routeId;
    }
  }, [route]);

  if (!route) return null;

  // [rerender-functional-setstate] Use functional setState for stable callbacks
  const handleStartNavigation = useCallback(() => {
    const sessionId = crypto.randomUUID();
    const sessionToken = crypto.randomUUID();
    const currentRoute = useRouteStore.getState().route;
    if (currentRoute) startNavigation(sessionId, sessionToken, currentRoute);
  }, [startNavigation]);

  const toggleCollapsed = useCallback(() => {
    setIsCollapsed((prev) => !prev);
  }, []);

  return (
    <div className={`route-panel ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="p-5">
        {/* Handle for collapsing - clickable */}
        <button
          onClick={toggleCollapsed}
          className="w-full flex flex-col items-center mb-2 py-2 -mt-2 hover:bg-slate-50 rounded-lg transition-colors cursor-pointer"
          aria-label={isCollapsed ? 'Expand panel' : 'Collapse panel'}
        >
          <div className="w-10 h-1 bg-slate-300 rounded-full mb-1" />
          {isCollapsed ? (
            <ChevronUp className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          )}
        </button>

        {/* Collapsed view - just show duration and buttons */}
        {isCollapsed ? (
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xl font-semibold text-slate-900">
                {formatDuration(route.summary?.durationSeconds ?? 0)}
              </span>
              <span className="text-sm text-slate-500 ml-2">
                {formatDistance(route.summary?.distanceMeters ?? 0)}
              </span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={clearRoute}
                className="h-10 px-4 rounded-xl font-medium text-sm bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors flex items-center gap-2"
              >
                <X className="w-4 h-4" />
              </button>
              <button
                onClick={handleStartNavigation}
                className="h-10 px-4 rounded-xl font-medium text-sm bg-accent-600 text-white hover:bg-accent-700 transition-colors flex items-center gap-2"
              >
                <Navigation className="w-4 h-4" />
                Start
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* Route Summary */}
            {route.summary && <RouteSummary summary={route.summary} />}

            {/* Route Options */}
            <RouteOptions />

            {/* Risk warnings */}
            {(route.riskAnalysis?.totalRiskZones ?? 0) > 0 && (
              <div className="mt-5 p-4 bg-caution-50 border border-caution-100 rounded-xl">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-caution-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <AlertTriangle className="w-4 h-4 text-caution-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800">
                      {route.riskAnalysis?.totalRiskZones ?? 0} risk zone{(route.riskAnalysis?.totalRiskZones ?? 0) > 1 ? 's' : ''} on route
                    </p>
                    {(route.riskAnalysis?.highSeverityZones ?? 0) > 0 && (
                      <p className="text-xs text-slate-500 mt-0.5">
                        Including {route.riskAnalysis?.highSeverityZones ?? 0} high-severity zone{(route.riskAnalysis?.highSeverityZones ?? 0) > 1 ? 's' : ''}
                      </p>
                    )}
                    <p className="text-xs text-slate-400 mt-1.5">
                      Audio warnings will sound when approaching
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Alternative routes */}
            {alternatives.length > 1 && (
              <div className="mt-5">
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
                  Alternative Routes
                </h3>
                <div className="space-y-2">
                  {alternatives.map((alt, index) => (
                    <button
                      key={alt.routeId}
                      className={`w-full p-3.5 rounded-xl border text-left transition-all duration-200 ${
                        alt.routeId === route.routeId
                          ? 'border-accent-500 bg-accent-50 ring-1 ring-accent-500/20'
                          : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                      }`}
                      onClick={() => useRouteStore.getState().setRoute(alt)}
                    >
                      <div className="flex justify-between items-center">
                        <span className={`text-sm font-medium ${
                          alt.routeId === route.routeId ? 'text-accent-700' : 'text-slate-700'
                        }`}>
                          {index === 0 ? 'Balanced' : index === 1 ? 'Safest' : 'Fastest'}
                        </span>
                        <div className="flex items-center gap-1.5">
                          <span className="text-sm text-slate-600">
                            {formatDuration(alt.summary?.durationSeconds ?? 0)}
                          </span>
                          <ChevronRight className={`w-4 h-4 ${
                            alt.routeId === route.routeId ? 'text-accent-500' : 'text-slate-300'
                          }`} />
                        </div>
                      </div>
                      <div className="text-xs text-slate-500 mt-1">
                        {formatDistance(alt.summary?.distanceMeters ?? 0)} · {(alt.summary?.bikeLanePercentage ?? 0).toFixed(0)}% bike lanes
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Action buttons */}
            <div className="mt-5 flex gap-3">
              <button
                onClick={clearRoute}
                className="flex-1 h-12 rounded-xl font-medium text-sm bg-slate-100 text-slate-700 hover:bg-slate-200 transition-colors flex items-center justify-center gap-2"
              >
                <X className="w-4 h-4" />
                Cancel
              </button>
              <button
                onClick={handleStartNavigation}
                className="flex-1 h-12 rounded-xl font-medium text-sm bg-accent-600 text-white hover:bg-accent-700 transition-colors flex items-center justify-center gap-2 active:scale-[0.98]"
              >
                <Navigation className="w-4 h-4" />
                Start
              </button>
            </div>
          </>
        )}
      </div>

      {/* Steep hill warning popup */}
      {showSteepHillWarning && (
        <SteepHillWarning
          maxGradePercent={route.summary?.maxGradePercent ?? 0}
          onDismiss={() => setShowSteepHillWarning(false)}
        />
      )}
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
