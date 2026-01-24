import { useRef, useCallback } from 'react';
import { useNavigationStore } from '../store/navigationStore';
import { RiskZone, HazardSeverity, HAZARD_TYPE_INFO } from '../types/riskZone';

// Alert sound URLs (would be actual audio files in production)
const ALERT_SOUNDS: Record<HazardSeverity, string> = {
  low: '/audio/alert-low.mp3',
  medium: '/audio/alert-medium.mp3',
  high: '/audio/alert-high.mp3',
  critical: '/audio/alert-critical.mp3',
};

export function useAudioAlerts() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const { audioEnabled } = useNavigationStore();

  const playAlertSound = useCallback(
    (severity: HazardSeverity) => {
      if (!audioEnabled) return;

      // Stop any current audio
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }

      // Create and play new audio
      const audio = new Audio(ALERT_SOUNDS[severity]);
      audioRef.current = audio;

      audio.play().catch((err) => {
        console.warn('Could not play alert sound:', err);
      });
    },
    [audioEnabled]
  );

  const speakAlert = useCallback(
    (message: string, severity: HazardSeverity) => {
      if (!audioEnabled || !('speechSynthesis' in window)) return;

      // Cancel any ongoing speech
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(message);

      // Adjust speech parameters based on severity
      utterance.rate = severity === 'critical' ? 1.2 : 1.0;
      utterance.pitch = severity === 'critical' ? 1.1 : 1.0;
      utterance.volume = 1.0;

      window.speechSynthesis.speak(utterance);
    },
    [audioEnabled]
  );

  const triggerRiskAlert = useCallback(
    (zone: RiskZone, distanceMeters: number) => {
      // Play alert sound first
      playAlertSound(zone.severity);

      // Build the alert message
      const hazardInfo = HAZARD_TYPE_INFO[zone.hazardType];
      const message =
        zone.alertMessage ||
        `${hazardInfo.label} ahead in ${Math.round(distanceMeters)} meters. Use caution.`;

      // Speak the alert after a short delay (so sound plays first)
      setTimeout(() => {
        speakAlert(message, zone.severity);
      }, 500);
    },
    [playAlertSound, speakAlert]
  );

  const speakManeuver = useCallback(
    (instruction: string) => {
      if (!audioEnabled || !('speechSynthesis' in window)) return;

      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(instruction);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      window.speechSynthesis.speak(utterance);
    },
    [audioEnabled]
  );

  const stopAlerts = useCallback(() => {
    // Stop audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }

    // Stop speech
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }, []);

  return {
    playAlertSound,
    speakAlert,
    triggerRiskAlert,
    speakManeuver,
    stopAlerts,
  };
}
