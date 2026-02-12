import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useRouteStore } from '../../store/routeStore';
import { RouteProfile } from '../../types';
import { Shield, Zap, Scale, Bike, Loader2 } from 'lucide-react';
import { calculateRoute } from '../../api/routing';

// [rendering-hoist-jsx] Hoist static config outside component
const PROFILE_OPTIONS: {
  value: RouteProfile;
  label: string;
  description: string;
  icon: typeof Shield;
}[] = [
  {
    value: 'balanced',
    label: 'Balanced',
    description: 'Balance safety and speed',
    icon: Scale,
  },
  {
    value: 'safest',
    label: 'Safest',
    description: 'Avoid risk zones efficiently',
    icon: Shield,
  },
  {
    value: 'fastest',
    label: 'Fastest',
    description: 'Shortest travel time',
    icon: Zap,
  },
];

// Bike lane thresholds for "Prefer Bike Lanes" feature
const BIKE_LANE_HIDE_THRESHOLD = 70; // Hide toggle when route already has 70%+ bike lanes
const BIKE_LANE_MIN_TARGET = 60; // Minimum target when toggle is enabled
const BIKE_LANE_HIGH_TARGET = 70; // Target when base route is 60-70%

export default function RouteOptions() {
  // [rerender-derived-state] Granular selectors prevent re-renders
  // when unrelated store fields change
  const preferences = useRouteStore((s) => s.preferences);
  const setPreferences = useRouteStore((s) => s.setPreferences);
  const origin = useRouteStore((s) => s.origin);
  const destination = useRouteStore((s) => s.destination);
  const route = useRouteStore((s) => s.route);
  const setRoute = useRouteStore((s) => s.setRoute);
  const setError = useRouteStore((s) => s.setError);

  const [isRecalculating, setIsRecalculating] = useState(false);
  const isSafest = preferences.profile === 'safest';
  const isFastest = preferences.profile === 'fastest';
  const isFirstRender = useRef(true);

  // Store the base route's bike lane percentage (before preferBikeLanes toggle)
  const [baseBikeLanePercentage, setBaseBikeLanePercentage] = useState<number | null>(null);

  // Determine if "Prefer Bike Lanes" toggle should be visible
  // Only show for SAFEST profile when route has < 70% bike lanes
  const showPreferBikeLanesToggle = useMemo(() => {
    if (!isSafest || !route) return false;

    // Use base percentage if we have it, otherwise use current route's percentage
    const bikeLanePercent = baseBikeLanePercentage ?? route.summary.bikeLanePercentage;

    // Hide if route already has excellent bike lane coverage
    return bikeLanePercent < BIKE_LANE_HIDE_THRESHOLD;
  }, [isSafest, route, baseBikeLanePercentage]);

  // Calculate what the target bike lane percentage should be
  const targetBikeLanePercentage = useMemo(() => {
    if (!route) return BIKE_LANE_MIN_TARGET;

    const currentPercent = baseBikeLanePercentage ?? route.summary.bikeLanePercentage;

    // If current is < 60%, target 60%
    // If current is 60-70%, target 70%
    if (currentPercent < BIKE_LANE_MIN_TARGET) {
      return BIKE_LANE_MIN_TARGET;
    } else if (currentPercent < BIKE_LANE_HIGH_TARGET) {
      return BIKE_LANE_HIGH_TARGET;
    }
    return currentPercent; // Already at or above 70%
  }, [route, baseBikeLanePercentage]);

  // Handle profile button click - recalculate route with new profile
  const handleProfileClick = useCallback(async (newProfile: RouteProfile) => {
    // Don't do anything if already selected or currently calculating
    if (newProfile === preferences.profile || isRecalculating) {
      return;
    }

    // Update the preference immediately for UI feedback
    const nextPreferences = {
      ...preferences,
      profile: newProfile,
      // Reset bike lanes toggle when switching profiles
      preferBikeLanes: false,
    };
    setPreferences(nextPreferences);

    // Reset base bike lane percentage when switching profiles
    setBaseBikeLanePercentage(null);

    // If we have origin and destination, recalculate the route
    if (origin && destination && route) {
      setIsRecalculating(true);
      setError(null);

      try {
        console.log('[RouteOptions] Calling calculateRoute with profile:', newProfile);
        const newRoute = await calculateRoute({
          origin,
          destination,
          vehicleType: 'scooter',
          preferences: nextPreferences,
          avoidRiskZones: true,
        });

        console.log('[RouteOptions] Route received:', {
          hasGeometry: !!newRoute?.geometry,
          coordsLength: newRoute?.geometry?.coordinates?.length,
          hasSummary: !!newRoute?.summary,
          summary: newRoute?.summary,
        });

        if (!newRoute?.geometry?.coordinates?.length) {
          throw new Error('Route could not be generated for this profile');
        }

        console.log('[RouteOptions] Setting route...');
        setRoute(newRoute);

        // Store the base bike lane percentage for this profile
        if (newProfile === 'safest') {
          setBaseBikeLanePercentage(newRoute.summary.bikeLanePercentage);
        }

        console.log('[RouteOptions] Route set successfully');
      } catch (error) {
        console.error('[RouteOptions] Failed to recalculate route:', error);
        setError(
          error instanceof Error
            ? error.message
            : 'Failed to recalculate route'
        );
      } finally {
        setIsRecalculating(false);
      }
    }
  }, [preferences, isRecalculating, origin, destination, route, setPreferences, setError, setRoute]);

  // Handle "Prefer Bike Lanes" toggle - recalculate with bike lane preference
  const handlePreferBikeLanesToggle = useCallback(async () => {
    if (isRecalculating || !origin || !destination) return;

    const newPreferBikeLanes = !preferences.preferBikeLanes;

    // Update preference immediately
    setPreferences({ preferBikeLanes: newPreferBikeLanes });

    // Recalculate route with new preference
    if (route) {
      setIsRecalculating(true);
      setError(null);

      try {
        console.log('[RouteOptions] Recalculating with preferBikeLanes:', newPreferBikeLanes);
        const newRoute = await calculateRoute({
          origin,
          destination,
          vehicleType: 'scooter',
          preferences: {
            ...preferences,
            preferBikeLanes: newPreferBikeLanes,
          },
          avoidRiskZones: true,
        });

        if (!newRoute?.geometry?.coordinates?.length) {
          throw new Error('Route could not be generated');
        }

        console.log('[RouteOptions] Bike lane route received:', {
          bikeLanePercentage: newRoute.summary.bikeLanePercentage,
          targetPercentage: targetBikeLanePercentage,
        });

        setRoute(newRoute);
      } catch (error) {
        console.error('[RouteOptions] Failed to recalculate bike lane route:', error);
        setError(
          error instanceof Error
            ? error.message
            : 'Failed to calculate bike lane route'
        );
        // Revert the toggle on error
        setPreferences({ preferBikeLanes: !newPreferBikeLanes });
      } finally {
        setIsRecalculating(false);
      }
    }
  }, [isRecalculating, origin, destination, preferences, route, targetBikeLanePercentage, setPreferences, setError, setRoute]);

  // Reset toggles when switching to Fastest
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    if (isFastest && preferences.preferBikeLanes) {
      setPreferences({ preferBikeLanes: false });
    }
  }, [isFastest, preferences.preferBikeLanes, setPreferences]);

  // Update base bike lane percentage when route changes and we're on safest without toggle
  useEffect(() => {
    if (isSafest && route && !preferences.preferBikeLanes && baseBikeLanePercentage === null) {
      setBaseBikeLanePercentage(route.summary.bikeLanePercentage);
    }
  }, [isSafest, route, preferences.preferBikeLanes, baseBikeLanePercentage]);

  return (
    <div className="mt-5">
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
        Route Preference
      </h3>

      {/* Profile selector */}
      <div className="flex gap-2">
        {PROFILE_OPTIONS.map((option) => {
          const Icon = option.icon;
          const isSelected = preferences.profile === option.value;
          const showSpinner = isRecalculating && isSelected;

          return (
            <button
              key={option.value}
              onClick={() => handleProfileClick(option.value)}
              disabled={isRecalculating}
              className={`flex-1 py-2.5 px-3 rounded-xl text-sm font-medium transition-all duration-200 flex flex-col items-center gap-1.5 ${
                isSelected
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              } ${isRecalculating ? 'cursor-wait' : ''}`}
              title={option.description}
            >
              {showSpinner ? (
                <Loader2 className="w-4 h-4 animate-spin text-white" />
              ) : (
                <Icon className={`w-4 h-4 ${isSelected ? 'text-white' : 'text-slate-400'}`} />
              )}
              <span>{option.label}</span>
            </button>
          );
        })}
      </div>

      {/* Prefer Bike Lanes toggle - ONLY for Safest profile when < 70% bike lanes */}
      {showPreferBikeLanesToggle && (
        <div className="mt-4 space-y-1">
          <button
            onClick={handlePreferBikeLanesToggle}
            disabled={isRecalculating}
            className={`w-full flex items-center justify-between p-3 -mx-3 rounded-lg hover:bg-slate-50 transition-all duration-200 ${
              isRecalculating ? 'opacity-50 cursor-wait' : ''
            }`}
          >
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors duration-200 ${
                preferences.preferBikeLanes
                  ? 'bg-emerald-100'
                  : 'bg-slate-100'
              }`}>
                {isRecalculating && preferences.preferBikeLanes ? (
                  <Loader2 className="w-4 h-4 text-emerald-600 animate-spin" />
                ) : (
                  <Bike className={`w-4 h-4 transition-colors duration-200 ${
                    preferences.preferBikeLanes ? 'text-emerald-600' : 'text-slate-400'
                  }`} />
                )}
              </div>
              <div className="text-left">
                <span className="text-sm font-medium text-slate-700 block">
                  Prefer Bike Lanes
                </span>
                <span className="text-xs text-slate-400">
                  {preferences.preferBikeLanes
                    ? `Prioritizing routes with ${targetBikeLanePercentage}%+ bike lanes`
                    : `Current route: ${Math.round(route?.summary.bikeLanePercentage ?? 0)}% bike lanes`}
                </span>
              </div>
            </div>
            <div
              className={`toggle-switch ${preferences.preferBikeLanes ? 'active emerald' : ''}`}
              role="switch"
              aria-checked={preferences.preferBikeLanes}
            />
          </button>
        </div>
      )}

      {/* Info message showing current bike lane % when toggle is hidden (already high) */}
      {isSafest && !showPreferBikeLanesToggle && route && (
        <div className="mt-4 flex items-center gap-2 text-xs text-emerald-600 justify-center">
          <Bike className="w-3.5 h-3.5" />
          <span>
            Route uses {Math.round(route.summary.bikeLanePercentage)}% bike lanes
          </span>
        </div>
      )}

      {/* Info message for Fastest */}
      {isFastest && (
        <p className="mt-4 text-xs text-slate-400 text-center">
          Fastest route optimizes for travel time
        </p>
      )}
    </div>
  );
}
