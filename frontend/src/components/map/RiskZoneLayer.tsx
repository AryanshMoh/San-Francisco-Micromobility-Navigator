import { useEffect, useState } from 'react';
import { Marker, Popup } from 'react-map-gl';
import { useMapStore } from '../../store/mapStore';
import { getRiskZonesInArea } from '../../api/riskZones';
import { RiskZone, SEVERITY_COLORS, HAZARD_TYPE_INFO, HazardType } from '../../types';
import {
  CircleDot,
  AlertTriangle,
  RotateCcw,
  SquareDashed,
  Construction,
  Car,
  Mountain,
  MoveHorizontal,
  DoorOpen,
  TrainTrack,
  CableCar,
  Bus,
  Users,
  Zap,
  LucideIcon,
} from 'lucide-react';

// Map icon names to Lucide components
const HAZARD_ICONS: Record<string, LucideIcon> = {
  'circle-dot': CircleDot,
  'alert-triangle': AlertTriangle,
  'rotate-ccw': RotateCcw,
  'square-dashed': SquareDashed,
  'construction': Construction,
  'car': Car,
  'mountain': Mountain,
  'move-horizontal': MoveHorizontal,
  'door-open': DoorOpen,
  'train-track': TrainTrack,
  'cable-car': CableCar,
  'bus': Bus,
  'users': Users,
  'zap': Zap,
};

function HazardIcon({ hazardType, className, style }: { hazardType: HazardType; className?: string; style?: React.CSSProperties }) {
  const iconName = HAZARD_TYPE_INFO[hazardType].iconName;
  const Icon = HAZARD_ICONS[iconName] || AlertTriangle;
  return <Icon className={className} style={style} />;
}

export default function RiskZoneLayer() {
  const [riskZones, setRiskZones] = useState<RiskZone[]>([]);
  const [selectedZone, setSelectedZone] = useState<RiskZone | null>(null);
  const { viewState } = useMapStore();

  // Fetch risk zones when map view changes
  useEffect(() => {
    const fetchZones = async () => {
      // Calculate bounding box from current view
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
              className="w-7 h-7 rounded-full flex items-center justify-center border-2 border-white shadow-md cursor-pointer transition-transform hover:scale-110"
              style={{ backgroundColor: color }}
              title={hazardInfo.label}
            >
              <HazardIcon hazardType={zone.hazardType} className="w-3.5 h-3.5 text-white" />
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
          <div className="p-3 min-w-[220px]">
            <div className="flex items-center gap-3 mb-3">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ backgroundColor: `${SEVERITY_COLORS[selectedZone.severity]}20` }}
              >
                <HazardIcon
                  hazardType={selectedZone.hazardType}
                  className="w-5 h-5"
                  style={{ color: SEVERITY_COLORS[selectedZone.severity] }}
                />
              </div>
              <div>
                <h3 className="font-semibold text-sm text-slate-800">
                  {HAZARD_TYPE_INFO[selectedZone.hazardType].label}
                </h3>
                <span
                  className="text-2xs px-2 py-0.5 rounded-full text-white font-medium uppercase tracking-wide"
                  style={{ backgroundColor: SEVERITY_COLORS[selectedZone.severity] }}
                >
                  {selectedZone.severity}
                </span>
              </div>
            </div>
            {selectedZone.description && (
              <p className="text-xs text-slate-500 leading-relaxed">{selectedZone.description}</p>
            )}
            {selectedZone.alertMessage && (
              <p className="text-xs text-slate-700 mt-2 font-medium">
                {selectedZone.alertMessage}
              </p>
            )}
            <p className="text-2xs text-slate-400 mt-3">
              Reported {selectedZone.reportedCount} time{selectedZone.reportedCount !== 1 ? 's' : ''}
            </p>
          </div>
        </Popup>
      )}
    </>
  );
}
