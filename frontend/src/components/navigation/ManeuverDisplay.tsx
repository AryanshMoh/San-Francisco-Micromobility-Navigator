import { Maneuver, ManeuverType } from '../../types/route';
import {
  ArrowUp,
  ArrowLeft,
  ArrowRight,
  CornerUpLeft,
  CornerUpRight,
  RotateCcw,
  GitMerge,
  GitFork,
  Circle,
  MapPin,
  Navigation,
} from 'lucide-react';

interface ManeuverDisplayProps {
  maneuver: Maneuver | null;
  distanceMeters: number;
  compact?: boolean;
}

const MANEUVER_ICONS: Record<ManeuverType, React.ComponentType<{ className?: string }>> = {
  depart: Navigation,
  arrive: MapPin,
  turn_left: ArrowLeft,
  turn_right: ArrowRight,
  slight_left: CornerUpLeft,
  slight_right: CornerUpRight,
  straight: ArrowUp,
  u_turn: RotateCcw,
  merge: GitMerge,
  fork: GitFork,
  roundabout: Circle,
};

export default function ManeuverDisplay({
  maneuver,
  distanceMeters,
  compact = false,
}: ManeuverDisplayProps) {
  if (!maneuver) {
    return (
      <div className={compact ? 'maneuver-compact' : 'maneuver-full'}>
        <div className={compact ? 'maneuver-icon-compact' : 'maneuver-icon-full'}>
          <Navigation className={compact ? 'w-5 h-5' : 'w-12 h-12'} />
        </div>
        {!compact && (
          <div className="maneuver-text-container">
            <span className="maneuver-instruction">Starting navigation...</span>
          </div>
        )}
      </div>
    );
  }

  const Icon = MANEUVER_ICONS[maneuver.type] || ArrowUp;
  const distanceFormatted = formatManeuverDistance(distanceMeters);
  const isArriving = maneuver.type === 'arrive';
  const isUrgent = distanceMeters < 50;

  if (compact) {
    return (
      <div className="maneuver-compact">
        <div className={`maneuver-icon-compact ${isUrgent ? 'maneuver-icon-urgent' : ''}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="maneuver-compact-text">
          <span className="maneuver-compact-distance">{distanceFormatted}</span>
          {maneuver.streetName && (
            <span className="maneuver-compact-street">{maneuver.streetName}</span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="maneuver-full">
      {/* Distance Callout */}
      <div className={`maneuver-distance-badge ${isUrgent ? 'maneuver-distance-urgent' : ''}`}>
        {distanceFormatted}
      </div>

      {/* Large Icon */}
      <div className={`maneuver-icon-container ${isArriving ? 'maneuver-icon-arrive' : ''} ${isUrgent ? 'maneuver-icon-urgent-full' : ''}`}>
        <div className="maneuver-icon-glow" />
        <Icon className="maneuver-icon-svg" />
      </div>

      {/* Instruction Text */}
      <div className="maneuver-text-container">
        <span className="maneuver-action">
          {getManeuverAction(maneuver.type)}
        </span>
        {maneuver.streetName && (
          <span className="maneuver-street">
            {maneuver.streetName}
          </span>
        )}
      </div>

      {/* Bike Lane Status */}
      {maneuver.bikeLaneStatus !== 'none' && (
        <div className={`maneuver-bike-lane-status ${maneuver.bikeLaneStatus}`}>
          {getBikeLaneMessage(maneuver.bikeLaneStatus)}
        </div>
      )}

      {/* Alerts */}
      {maneuver.alerts.length > 0 && (
        <div className="maneuver-alerts">
          {maneuver.alerts.map((alert, i) => (
            <div key={i} className={`maneuver-alert maneuver-alert-${alert.severity}`}>
              {alert.message}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function formatManeuverDistance(meters: number): string {
  if (meters < 10) {
    return 'Now';
  }
  if (meters < 100) {
    return `${Math.round(meters / 10) * 10} ft`;
  }
  if (meters < 1000) {
    const feet = Math.round(meters * 3.281);
    if (feet < 500) {
      return `${Math.round(feet / 50) * 50} ft`;
    }
    return `${Math.round(feet / 100) * 100} ft`;
  }
  const miles = meters / 1609.34;
  if (miles < 0.5) {
    return `${(miles * 5280 / 100).toFixed(0)}00 ft`;
  }
  return `${miles.toFixed(1)} mi`;
}

function getManeuverAction(type: ManeuverType): string {
  const actions: Record<ManeuverType, string> = {
    depart: 'Head towards',
    arrive: 'Arrive at',
    turn_left: 'Turn left onto',
    turn_right: 'Turn right onto',
    slight_left: 'Bear left onto',
    slight_right: 'Bear right onto',
    straight: 'Continue on',
    u_turn: 'Make a U-turn onto',
    merge: 'Merge onto',
    fork: 'Take the fork onto',
    roundabout: 'Enter roundabout for',
  };
  return actions[type] || 'Continue on';
}

function getBikeLaneMessage(status: string): string {
  switch (status) {
    case 'entering':
      return '🚴 Entering bike lane';
    case 'leaving':
      return '⚠️ Leaving bike lane';
    case 'continuing':
      return '🚴 Bike lane continues';
    default:
      return '';
  }
}
