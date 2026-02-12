import { useMapStore } from '../../store/mapStore';
import { Layers, Bike, AlertCircle } from 'lucide-react';

export default function MapControls() {
  const {
    showBikeLanes,
    showRiskZones,
    setShowBikeLanes,
    setShowRiskZones,
  } = useMapStore();

  return (
    <div className="map-controls">
      <div className="bg-white rounded-xl shadow-soft p-4 w-52">
        {/* Header */}
        <div className="flex items-center gap-2 mb-4">
          <Layers className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Layers
          </span>
        </div>

        {/* Toggle Controls */}
        <div className="space-y-3">
          {/* Bike Lanes Toggle */}
          <button
            onClick={() => setShowBikeLanes(!showBikeLanes)}
            className="w-full flex items-center justify-between p-2 -mx-2 rounded-lg hover:bg-slate-50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
                showBikeLanes ? 'bg-accent-100' : 'bg-slate-100'
              }`}>
                <Bike className={`w-4 h-4 transition-colors ${
                  showBikeLanes ? 'text-accent-600' : 'text-slate-400'
                }`} />
              </div>
              <span className={`text-sm font-medium transition-colors ${
                showBikeLanes ? 'text-slate-800' : 'text-slate-600'
              }`}>
                Bike Lanes
              </span>
            </div>
            <div
              className={`toggle-switch ${showBikeLanes ? 'active' : ''}`}
              role="switch"
              aria-checked={showBikeLanes}
            />
          </button>

          {/* Risk Zones Toggle */}
          <button
            onClick={() => setShowRiskZones(!showRiskZones)}
            className="w-full flex items-center justify-between p-2 -mx-2 rounded-lg hover:bg-slate-50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
                showRiskZones ? 'bg-alert-100' : 'bg-slate-100'
              }`}>
                <AlertCircle className={`w-4 h-4 transition-colors ${
                  showRiskZones ? 'text-alert-500' : 'text-slate-400'
                }`} />
              </div>
              <span className={`text-sm font-medium transition-colors ${
                showRiskZones ? 'text-slate-800' : 'text-slate-600'
              }`}>
                Risk Zones
              </span>
            </div>
            <div
              className={`toggle-switch ${showRiskZones ? 'active' : ''}`}
              role="switch"
              aria-checked={showRiskZones}
            />
          </button>
        </div>

        {/* Legend */}
        {(showBikeLanes || showRiskZones) && (
          <div className="mt-4 pt-4 border-t border-slate-100">
            <span className="text-2xs font-medium text-slate-400 uppercase tracking-wider">
              Legend
            </span>
            <div className="mt-2.5 space-y-2">
              {showBikeLanes && (
                <>
                  {/* Class I - Off-street paths */}
                  <div className="flex items-center gap-2.5">
                    <div className="w-6 h-1.5 rounded-full" style={{ backgroundColor: '#059669' }} />
                    <span className="text-xs text-slate-600">Bike Path</span>
                    <span className="text-2xs text-slate-400 ml-auto">Class I</span>
                  </div>
                  {/* Class IV - Protected bikeways */}
                  <div className="flex items-center gap-2.5">
                    <div className="w-6 h-1.5 rounded-full" style={{ backgroundColor: '#10b981' }} />
                    <span className="text-xs text-slate-600">Protected</span>
                    <span className="text-2xs text-slate-400 ml-auto">Class IV</span>
                  </div>
                  {/* Class II - Painted lanes */}
                  <div className="flex items-center gap-2.5">
                    <div className="w-6 h-1 rounded-full" style={{ backgroundColor: '#22c55e' }} />
                    <span className="text-xs text-slate-600">Bike Lane</span>
                    <span className="text-2xs text-slate-400 ml-auto">Class II</span>
                  </div>
                </>
              )}
              {showRiskZones && (
                <>
                  {showBikeLanes && <div className="h-1" />}
                  {/* Dark Red */}
                  <div className="flex items-center gap-2.5">
                    <div className="w-4 h-4 rounded-full" style={{ backgroundColor: '#b91c1c', opacity: 0.7 }} />
                    <span className="text-xs text-slate-600">Moderate-High Risk</span>
                  </div>
                  {/* Light Red */}
                  <div className="flex items-center gap-2.5">
                    <div className="w-4 h-4 rounded-full" style={{ backgroundColor: '#dc2626', opacity: 0.7 }} />
                    <span className="text-xs text-slate-600">Moderate Risk</span>
                  </div>
                  {/* Yellow */}
                  <div className="flex items-center gap-2.5">
                    <div className="w-4 h-4 rounded-full" style={{ backgroundColor: '#eab308', opacity: 0.7 }} />
                    <span className="text-xs text-slate-600">Low Risk</span>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
