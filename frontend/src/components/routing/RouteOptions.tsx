import { useRouteStore } from '../../store/routeStore';
import { RouteProfile } from '../../types';

const PROFILE_OPTIONS: { value: RouteProfile; label: string; description: string }[] = [
  {
    value: 'safest',
    label: 'Safest',
    description: 'Prioritize bike lanes and avoid risks',
  },
  {
    value: 'fastest',
    label: 'Fastest',
    description: 'Shortest travel time',
  },
  {
    value: 'balanced',
    label: 'Balanced',
    description: 'Balance safety and speed',
  },
];

export default function RouteOptions() {
  const { preferences, setPreferences } = useRouteStore();

  return (
    <div className="mt-4">
      <h3 className="text-sm font-medium text-gray-600 mb-2">Route Preference</h3>

      {/* Profile selector */}
      <div className="flex gap-2 mb-4">
        {PROFILE_OPTIONS.map((option) => (
          <button
            key={option.value}
            onClick={() => setPreferences({ profile: option.value })}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${
              preferences.profile === option.value
                ? 'bg-primary-100 text-primary-700 border-2 border-primary-500'
                : 'bg-gray-100 text-gray-600 border-2 border-transparent hover:bg-gray-200'
            }`}
            title={option.description}
          >
            {option.label}
          </button>
        ))}
      </div>

      {/* Toggle options */}
      <div className="space-y-3">
        <label className="flex items-center justify-between cursor-pointer">
          <div>
            <span className="text-sm text-gray-700">Avoid steep hills</span>
            <p className="text-xs text-gray-500">Prefer flatter routes</p>
          </div>
          <input
            type="checkbox"
            checked={preferences.avoidHills}
            onChange={(e) => setPreferences({ avoidHills: e.target.checked })}
            className="rounded text-primary-600 focus:ring-primary-500 h-5 w-5"
          />
        </label>

        <label className="flex items-center justify-between cursor-pointer">
          <div>
            <span className="text-sm text-gray-700">Prefer bike lanes</span>
            <p className="text-xs text-gray-500">Stay on dedicated bike infrastructure</p>
          </div>
          <input
            type="checkbox"
            checked={preferences.preferBikeLanes}
            onChange={(e) => setPreferences({ preferBikeLanes: e.target.checked })}
            className="rounded text-primary-600 focus:ring-primary-500 h-5 w-5"
          />
        </label>
      </div>

      {/* Bike lane preference slider */}
      {preferences.preferBikeLanes && (
        <div className="mt-3">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>Allow some roads</span>
            <span>Bike lanes only</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={preferences.bikeLaneWeight}
            onChange={(e) =>
              setPreferences({ bikeLaneWeight: parseFloat(e.target.value) })
            }
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
          />
        </div>
      )}
    </div>
  );
}
