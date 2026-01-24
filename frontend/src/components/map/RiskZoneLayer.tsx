import { useEffect, useState } from 'react';
import { Marker, Popup } from 'react-map-gl';
import { useMapStore } from '../../store/mapStore';
import { getRiskZonesInArea } from '../../api/riskZones';
import { RiskZone, SEVERITY_COLORS, HAZARD_TYPE_INFO } from '../../types';

export default function RiskZoneLayer() {
  const [riskZones, setRiskZones] = useState<RiskZone[]>([]);
  const [selectedZone, setSelectedZone] = useState<RiskZone | null>(null);
  const { viewState } = useMapStore();

  // Fetch risk zones when map view changes
  useEffect(() => {
    const fetchZones = async () => {
      // Calculate bounding box from current view
      // This is a simplified calculation - in production you'd use the actual map bounds
      const buffer = 0.05; // roughly 5km at SF latitude
      const bbox = [
        viewState.longitude - buffer,
        viewState.latitude - buffer,
        viewState.longitude + buffer,
        viewState.latitude + buffer,
      ].join(',');

      try {
        const zones = await getRiskZonesInArea(bbox);
        setRiskZones(zones);
      } catch (error) {
        console.error('Failed to fetch risk zones:', error);
      }
    };

    // Debounce the fetch
    const timeoutId = setTimeout(fetchZones, 500);
    return () => clearTimeout(timeoutId);
  }, [viewState.longitude, viewState.latitude, viewState.zoom]);

  return (
    <>
      {riskZones.map((zone) => {
        // Get coordinates from geometry
        let coords: [number, number] = [0, 0];
        if (zone.geometry.type === 'Point') {
          coords = zone.geometry.coordinates as [number, number];
        }

        const hazardInfo = HAZARD_TYPE_INFO[zone.hazardType];
        const color = SEVERITY_COLORS[zone.severity];

        return (
          <Marker
            key={zone.id}
            longitude={coords[0]}
            latitude={coords[1]}
            anchor="center"
            onClick={(e) => {
              e.originalEvent.stopPropagation();
              setSelectedZone(zone);
            }}
          >
            <div
              className="risk-zone-marker"
              style={{ backgroundColor: color }}
              title={hazardInfo.label}
            >
              <span className="text-xs">{hazardInfo.icon}</span>
            </div>
          </Marker>
        );
      })}

      {/* Popup for selected zone */}
      {selectedZone && selectedZone.geometry.type === 'Point' && (
        <Popup
          longitude={selectedZone.geometry.coordinates[0]}
          latitude={selectedZone.geometry.coordinates[1]}
          anchor="bottom"
          onClose={() => setSelectedZone(null)}
          closeButton
          closeOnClick={false}
        >
          <div className="p-2 min-w-[200px]">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl">
                {HAZARD_TYPE_INFO[selectedZone.hazardType].icon}
              </span>
              <div>
                <h3 className="font-semibold text-sm">
                  {HAZARD_TYPE_INFO[selectedZone.hazardType].label}
                </h3>
                <span
                  className="text-xs px-2 py-0.5 rounded-full text-white"
                  style={{ backgroundColor: SEVERITY_COLORS[selectedZone.severity] }}
                >
                  {selectedZone.severity}
                </span>
              </div>
            </div>
            {selectedZone.description && (
              <p className="text-xs text-gray-600 mt-1">{selectedZone.description}</p>
            )}
            {selectedZone.alertMessage && (
              <p className="text-xs text-gray-800 mt-1 font-medium">
                {selectedZone.alertMessage}
              </p>
            )}
            <p className="text-xs text-gray-400 mt-2">
              Reported {selectedZone.reportedCount} time(s)
            </p>
          </div>
        </Popup>
      )}
    </>
  );
}
