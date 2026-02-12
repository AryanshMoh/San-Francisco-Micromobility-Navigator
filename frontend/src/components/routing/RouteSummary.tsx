import { memo } from 'react';
import { RouteSummary as RouteSummaryType } from '../../types';
import { Route, Bike, TrendingUp, TrendingDown, Mountain } from 'lucide-react';

interface RouteSummaryProps {
  summary: RouteSummaryType;
}

// [rerender-memo] Memoize to prevent re-renders when RoutePanel state changes
export default memo(function RouteSummary({ summary }: RouteSummaryProps) {
  // Defensive defaults for all values
  const durationSeconds = summary?.durationSeconds ?? 0;
  const distanceMeters = summary?.distanceMeters ?? 0;
  const bikeLanePercentage = summary?.bikeLanePercentage ?? 0;
  const elevationGainMeters = summary?.elevationGainMeters ?? 0;
  const elevationLossMeters = summary?.elevationLossMeters ?? 0;
  const maxGradePercent = summary?.maxGradePercent ?? 0;

  return (
    <div className="bg-slate-50 rounded-xl p-4">
      {/* Main stats */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-semibold text-slate-900 tracking-tight">
              {formatDuration(durationSeconds)}
            </span>
          </div>
          <div className="flex items-center gap-1.5 mt-0.5">
            <Route className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-sm text-slate-500">
              {formatDistance(distanceMeters)}
            </span>
          </div>
        </div>

        <div className="text-right">
          <div className="flex items-center gap-1.5 justify-end">
            <div className="w-7 h-7 bg-accent-100 rounded-lg flex items-center justify-center">
              <Bike className="w-4 h-4 text-accent-600" />
            </div>
            <span className="text-lg font-semibold text-accent-600">
              {bikeLanePercentage.toFixed(0)}%
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">bike lanes</p>
        </div>
      </div>

      {/* Detailed stats */}
      <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-slate-200/60">
        {/* Elevation gain */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-sm font-medium text-slate-700">
              {elevationGainMeters}m
            </span>
          </div>
          <p className="text-2xs text-slate-400 mt-0.5">climb</p>
        </div>

        {/* Elevation loss */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-1.5">
            <TrendingDown className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-sm font-medium text-slate-700">
              {elevationLossMeters}m
            </span>
          </div>
          <p className="text-2xs text-slate-400 mt-0.5">descent</p>
        </div>

        {/* Max grade */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-1.5">
            <Mountain className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-sm font-medium text-slate-700">
              {maxGradePercent.toFixed(0)}%
            </span>
          </div>
          <p className="text-2xs text-slate-400 mt-0.5">max grade</p>
        </div>
      </div>

    </div>
  );
});

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
