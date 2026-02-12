import { MapPin, Clock, Bike } from 'lucide-react';

interface NavigationStatsProps {
  distanceRemaining: number;
  durationRemaining: number;
  bikeLanePercentage: number;
}

export default function NavigationStats({
  distanceRemaining,
  durationRemaining,
  bikeLanePercentage,
}: NavigationStatsProps) {
  return (
    <div className="nav-stats-bar">
      {/* Distance */}
      <div className="nav-stat">
        <div className="nav-stat-icon">
          <MapPin className="w-4 h-4" />
        </div>
        <div className="nav-stat-content">
          <span className="nav-stat-value">{formatDistance(distanceRemaining)}</span>
          <span className="nav-stat-label">remaining</span>
        </div>
      </div>

      {/* Divider */}
      <div className="nav-stat-divider" />

      {/* ETA */}
      <div className="nav-stat">
        <div className="nav-stat-icon">
          <Clock className="w-4 h-4" />
        </div>
        <div className="nav-stat-content">
          <span className="nav-stat-value">{formatArrivalTime(durationRemaining)}</span>
          <span className="nav-stat-label">arrival</span>
        </div>
      </div>

      {/* Divider */}
      <div className="nav-stat-divider" />

      {/* Bike Lane Coverage */}
      <div className="nav-stat">
        <div className="nav-stat-icon nav-stat-icon-bike">
          <Bike className="w-4 h-4" />
        </div>
        <div className="nav-stat-content">
          <span className="nav-stat-value">{Math.round(bikeLanePercentage)}%</span>
          <span className="nav-stat-label">bike lanes</span>
        </div>
        {/* Mini progress bar */}
        <div className="nav-stat-progress">
          <div
            className="nav-stat-progress-fill"
            style={{ width: `${bikeLanePercentage}%` }}
          />
        </div>
      </div>
    </div>
  );
}

function formatDistance(meters: number): string {
  if (meters < 1000) {
    return `${Math.round(meters)} m`;
  }
  const miles = meters / 1609.34;
  return `${miles.toFixed(1)} mi`;
}

function formatArrivalTime(secondsRemaining: number): string {
  const arrival = new Date(Date.now() + secondsRemaining * 1000);
  return arrival.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}
