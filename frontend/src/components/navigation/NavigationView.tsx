import { useEffect, useCallback, useState, useRef } from 'react';
import { useNavigationStore } from '../../store/navigationStore';
import { useMapStore } from '../../store/mapStore';
import { Coordinate } from '../../types/route';
import ManeuverDisplay from './ManeuverDisplay';
import NavigationStats from './NavigationStats';
import RiskZoneAlert from './RiskZoneAlert';
import NavigationControls from './NavigationControls';
import { useNavigationTracking } from '../../hooks/useNavigationTracking';
import { X, ChevronUp, ChevronDown } from 'lucide-react';

export default function NavigationView() {
  const {
    isActive,
    route,
    nextManeuver,
    distanceToManeuverMeters,
    distanceRemainingMeters,
    durationRemainingSeconds,
    approachingRiskZones,
    onRoute,
    audioEnabled,
    currentLocation,
    speedMps,
    endNavigation,
    toggleAudio,
  } = useNavigationStore();

  const { flyTo, setViewState } = useMapStore();
  const [isExpanded, setIsExpanded] = useState(true);
  const [showExitConfirm, setShowExitConfirm] = useState(false);
  const lastLocationRef = useRef<Coordinate | null>(null);

  // Start location tracking
  useNavigationTracking();

  // Follow user location on map
  useEffect(() => {
    if (currentLocation && isActive) {
      const hasMovedSignificantly = !lastLocationRef.current ||
        Math.abs(currentLocation.latitude - lastLocationRef.current.latitude) > 0.00005 ||
        Math.abs(currentLocation.longitude - lastLocationRef.current.longitude) > 0.00005;

      if (hasMovedSignificantly) {
        setViewState({
          longitude: currentLocation.longitude,
          latitude: currentLocation.latitude,
          zoom: 17,
          pitch: 45,
          bearing: useNavigationStore.getState().heading || 0,
        });
        lastLocationRef.current = currentLocation;
      }
    }
  }, [currentLocation, isActive, setViewState]);

  // Center on route start when navigation begins
  useEffect(() => {
    if (isActive && route && route.geometry.coordinates.length > 0) {
      const [lng, lat] = route.geometry.coordinates[0];
      flyTo(lng, lat, 16);
    }
  }, [isActive, route, flyTo]);

  const handleExit = useCallback(() => {
    setShowExitConfirm(true);
  }, []);

  const confirmExit = useCallback(() => {
    endNavigation();
    setShowExitConfirm(false);
    // Reset map view
    setViewState({ pitch: 0, bearing: 0, zoom: 13 });
  }, [endNavigation, setViewState]);

  const cancelExit = useCallback(() => {
    setShowExitConfirm(false);
  }, []);

  if (!isActive || !route) return null;

  const currentSpeed = speedMps ? Math.round(speedMps * 2.237) : 0; // m/s to mph

  return (
    <div className="navigation-view">
      {/* Risk Zone Alert Overlay */}
      {approachingRiskZones.length > 0 && (
        <RiskZoneAlert
          zones={approachingRiskZones}
          audioEnabled={audioEnabled}
        />
      )}

      {/* Off-Route Warning */}
      {!onRoute && (
        <div className="off-route-banner">
          <div className="off-route-content">
            <div className="off-route-pulse" />
            <span className="off-route-text">Off Route</span>
            <span className="off-route-subtext">Recalculating...</span>
          </div>
        </div>
      )}

      {/* Top Navigation Bar - Minimized View */}
      <div
        className={`nav-top-bar ${isExpanded ? 'nav-top-bar-hidden' : ''}`}
        onClick={() => setIsExpanded(true)}
      >
        <div className="nav-top-bar-content">
          <div className="nav-mini-maneuver">
            <ManeuverDisplay
              maneuver={nextManeuver}
              distanceMeters={distanceToManeuverMeters}
              compact
            />
          </div>
          <div className="nav-mini-eta">
            <span className="nav-mini-eta-time">
              {formatETA(durationRemainingSeconds)}
            </span>
            <ChevronDown className="w-5 h-5 text-slate-400" />
          </div>
        </div>
      </div>

      {/* Main Navigation Panel - Expanded View */}
      <div className={`nav-main-panel ${isExpanded ? '' : 'nav-main-panel-hidden'}`}>
        {/* Drag Handle */}
        <div
          className="nav-drag-handle"
          onClick={() => setIsExpanded(false)}
        >
          <div className="nav-handle-bar" />
          <ChevronUp className="w-5 h-5 text-slate-500 mt-1" />
        </div>

        {/* Primary Maneuver Display */}
        <div className="nav-maneuver-section">
          <ManeuverDisplay
            maneuver={nextManeuver}
            distanceMeters={distanceToManeuverMeters}
          />
        </div>

        {/* Current Speed */}
        <div className="nav-speed-indicator">
          <span className="nav-speed-value">{currentSpeed}</span>
          <span className="nav-speed-unit">mph</span>
        </div>

        {/* Stats Bar */}
        <NavigationStats
          distanceRemaining={distanceRemainingMeters}
          durationRemaining={durationRemainingSeconds}
          bikeLanePercentage={route.summary.bikeLanePercentage}
        />

        {/* Controls */}
        <NavigationControls
          audioEnabled={audioEnabled}
          onToggleAudio={toggleAudio}
          onExit={handleExit}
        />
      </div>

      {/* Exit Confirmation Modal */}
      {showExitConfirm && (
        <div className="nav-exit-modal-overlay" onClick={cancelExit}>
          <div
            className="nav-exit-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="nav-exit-icon">
              <X className="w-8 h-8" />
            </div>
            <h3 className="nav-exit-title">End Navigation?</h3>
            <p className="nav-exit-subtitle">
              You'll lose your current route progress.
            </p>
            <div className="nav-exit-buttons">
              <button
                className="nav-exit-btn nav-exit-btn-cancel"
                onClick={cancelExit}
              >
                Continue
              </button>
              <button
                className="nav-exit-btn nav-exit-btn-confirm"
                onClick={confirmExit}
              >
                End
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function formatETA(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}
