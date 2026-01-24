import { RouteSummary as RouteSummaryType } from '../../types';

interface RouteSummaryProps {
  summary: RouteSummaryType;
}

export default function RouteSummary({ summary }: RouteSummaryProps) {
  return (
    <div className="bg-gray-50 rounded-lg p-4">
      {/* Main stats */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-2xl font-bold text-gray-900">
            {formatDuration(summary.durationSeconds)}
          </p>
          <p className="text-sm text-gray-500">
            {formatDistance(summary.distanceMeters)}
          </p>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1 text-primary-600">
            <span className="text-lg">🚴</span>
            <span className="font-medium">
              {summary.bikeLanePercentage.toFixed(0)}%
            </span>
          </div>
          <p className="text-xs text-gray-500">bike lanes</p>
        </div>
      </div>

      {/* Detailed stats */}
      <div className="grid grid-cols-3 gap-4 pt-3 border-t border-gray-200">
        {/* Elevation gain */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 text-gray-700">
            <span>↗️</span>
            <span className="font-medium">{summary.elevationGainMeters}m</span>
          </div>
          <p className="text-xs text-gray-500">climb</p>
        </div>

        {/* Elevation loss */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 text-gray-700">
            <span>↘️</span>
            <span className="font-medium">{summary.elevationLossMeters}m</span>
          </div>
          <p className="text-xs text-gray-500">descent</p>
        </div>

        {/* Max grade */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 text-gray-700">
            <span>⛰️</span>
            <span className="font-medium">{summary.maxGradePercent.toFixed(0)}%</span>
          </div>
          <p className="text-xs text-gray-500">max grade</p>
        </div>
      </div>

      {/* Safety score */}
      <div className="mt-4 pt-3 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600">Safety Score</span>
          <SafetyIndicator score={1 - summary.riskScore} />
        </div>
      </div>
    </div>
  );
}

function SafetyIndicator({ score }: { score: number }) {
  // Score is 0-1 where 1 is safest
  const percentage = score * 100;
  const color =
    percentage >= 80
      ? 'bg-green-500'
      : percentage >= 60
      ? 'bg-yellow-500'
      : percentage >= 40
      ? 'bg-orange-500'
      : 'bg-red-500';

  const label =
    percentage >= 80
      ? 'Safe'
      : percentage >= 60
      ? 'Moderate'
      : percentage >= 40
      ? 'Caution'
      : 'Risky';

  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${color} rounded-full transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-sm font-medium text-gray-700">{label}</span>
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
