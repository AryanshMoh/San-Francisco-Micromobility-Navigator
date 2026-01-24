import { useMapStore } from '../../store/mapStore';

export default function MapControls() {
  const {
    showBikeLanes,
    showRiskZones,
    showTraffic,
    setShowBikeLanes,
    setShowRiskZones,
    setShowTraffic,
  } = useMapStore();

  return (
    <div className="absolute top-16 right-4 z-10">
      <div className="bg-white rounded-lg shadow-lg p-3 space-y-2">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          Layers
        </h3>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showBikeLanes}
            onChange={(e) => setShowBikeLanes(e.target.checked)}
            className="rounded text-primary-600 focus:ring-primary-500"
          />
          <span className="text-sm">Bike Lanes</span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showRiskZones}
            onChange={(e) => setShowRiskZones(e.target.checked)}
            className="rounded text-primary-600 focus:ring-primary-500"
          />
          <span className="text-sm">Risk Zones</span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showTraffic}
            onChange={(e) => setShowTraffic(e.target.checked)}
            className="rounded text-primary-600 focus:ring-primary-500"
          />
          <span className="text-sm">Traffic</span>
        </label>
      </div>
    </div>
  );
}
