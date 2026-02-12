import { useEffect, useRef } from 'react';
import { ApproachingRiskZone } from '../../types/navigation';
import { HAZARD_TYPE_INFO, SEVERITY_COLORS } from '../../types/riskZone';
import {
  AlertTriangle,
  CircleDot,
  RotateCcw,
  Construction,
  Car,
  Mountain,
  MoveHorizontal,
  DoorOpen,
  TrainTrack,
  Bus,
  Users,
  Zap,
} from 'lucide-react';

interface RiskZoneAlertProps {
  zones: ApproachingRiskZone[];
  audioEnabled: boolean;
}

// Map icon names to actual components
const HAZARD_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  'circle-dot': CircleDot,
  'alert-triangle': AlertTriangle,
  'rotate-ccw': RotateCcw,
  'square-dashed': AlertTriangle,
  construction: Construction,
  car: Car,
  mountain: Mountain,
  'move-horizontal': MoveHorizontal,
  'door-open': DoorOpen,
  'train-track': TrainTrack,
  'cable-car': TrainTrack,
  bus: Bus,
  users: Users,
  zap: Zap,
};

export default function RiskZoneAlert({ zones, audioEnabled }: RiskZoneAlertProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const lastAlertRef = useRef<string | null>(null);

  // Play alert sound for new zones
  useEffect(() => {
    if (!audioEnabled || zones.length === 0) return;

    const mostUrgent = zones.reduce((prev, curr) =>
      curr.distanceMeters < prev.distanceMeters ? curr : prev
    );

    // Only play if this is a new zone or we're much closer
    if (
      lastAlertRef.current !== mostUrgent.riskZone.id ||
      mostUrgent.distanceMeters < 30
    ) {
      playAlertSound(mostUrgent.riskZone.severity);
      lastAlertRef.current = mostUrgent.riskZone.id;
    }
  }, [zones, audioEnabled]);

  if (zones.length === 0) return null;

  // Show the most urgent (closest) zone prominently
  const primaryZone = zones.reduce((prev, curr) =>
    curr.distanceMeters < prev.distanceMeters ? curr : prev
  );

  const hazardInfo = HAZARD_TYPE_INFO[primaryZone.riskZone.hazardType];
  const Icon = HAZARD_ICONS[hazardInfo?.iconName || 'alert-triangle'] || AlertTriangle;
  const severityColor = SEVERITY_COLORS[primaryZone.riskZone.severity];

  const isImmediate = primaryZone.distanceMeters < 30;
  const isClose = primaryZone.distanceMeters < 100;

  return (
    <div className={`risk-alert-overlay ${isImmediate ? 'risk-alert-immediate' : ''}`}>
      <div
        className={`risk-alert-card ${isImmediate ? 'risk-alert-card-immediate' : isClose ? 'risk-alert-card-close' : ''}`}
        style={{
          '--severity-color': severityColor,
          '--severity-glow': `${severityColor}40`,
        } as React.CSSProperties}
      >
        {/* Pulsing background for immediate danger */}
        {isImmediate && <div className="risk-alert-pulse-bg" />}

        {/* Icon */}
        <div className="risk-alert-icon-container">
          <div className="risk-alert-icon-glow" />
          <Icon className="risk-alert-icon" />
        </div>

        {/* Content */}
        <div className="risk-alert-content">
          <div className="risk-alert-header">
            <span className="risk-alert-label">
              {isImmediate ? 'CAUTION' : 'AHEAD'}
            </span>
            <span className="risk-alert-distance">
              {formatAlertDistance(primaryZone.distanceMeters)}
            </span>
          </div>

          <h3 className="risk-alert-title">
            {hazardInfo?.label || 'Risk Zone'}
          </h3>

          {primaryZone.riskZone.alertMessage && (
            <p className="risk-alert-message">
              {primaryZone.riskZone.alertMessage}
            </p>
          )}

          {/* Severity indicator */}
          <div className="risk-alert-severity">
            <span
              className="risk-alert-severity-dot"
              style={{ backgroundColor: severityColor }}
            />
            <span className="risk-alert-severity-text">
              {primaryZone.riskZone.severity.charAt(0).toUpperCase() +
                primaryZone.riskZone.severity.slice(1)} Risk
            </span>
          </div>
        </div>

        {/* Additional zones indicator */}
        {zones.length > 1 && (
          <div className="risk-alert-more">
            +{zones.length - 1} more ahead
          </div>
        )}
      </div>

      {/* Hidden audio element */}
      <audio ref={audioRef} />
    </div>
  );
}

function formatAlertDistance(meters: number): string {
  if (meters < 10) return 'Now';
  if (meters < 100) return `${Math.round(meters / 10) * 10} ft`;
  const feet = Math.round(meters * 3.281);
  return `${Math.round(feet / 100) * 100} ft`;
}

function playAlertSound(severity: string) {
  // Use Web Audio API for reliable, low-latency audio
  try {
    const audioContext = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    // Different sounds based on severity
    const frequencies: Record<string, number[]> = {
      critical: [880, 440, 880], // Urgent alternating
      high: [660, 440],
      medium: [440],
      low: [330],
    };

    const freqs = frequencies[severity] || frequencies.medium;
    const duration = severity === 'critical' ? 0.15 : 0.2;

    oscillator.type = 'sine';
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);

    let time = audioContext.currentTime;
    freqs.forEach((freq, i) => {
      oscillator.frequency.setValueAtTime(freq, time + i * duration);
    });

    gainNode.gain.exponentialRampToValueAtTime(
      0.01,
      audioContext.currentTime + freqs.length * duration
    );

    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + freqs.length * duration);
  } catch {
    // Audio API not available, fail silently
  }
}
