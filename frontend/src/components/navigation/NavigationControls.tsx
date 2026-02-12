import { Volume2, VolumeX, X, MoreVertical, Flag, AlertCircle } from 'lucide-react';
import { useState } from 'react';

interface NavigationControlsProps {
  audioEnabled: boolean;
  onToggleAudio: () => void;
  onExit: () => void;
}

export default function NavigationControls({
  audioEnabled,
  onToggleAudio,
  onExit,
}: NavigationControlsProps) {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div className="nav-controls">
      {/* Audio Toggle */}
      <button
        className={`nav-control-btn ${audioEnabled ? 'nav-control-btn-active' : ''}`}
        onClick={onToggleAudio}
        title={audioEnabled ? 'Mute alerts' : 'Enable alerts'}
      >
        {audioEnabled ? (
          <Volume2 className="w-5 h-5" />
        ) : (
          <VolumeX className="w-5 h-5" />
        )}
        <span className="nav-control-label">
          {audioEnabled ? 'Sound On' : 'Muted'}
        </span>
      </button>

      {/* More Options */}
      <div className="nav-control-menu-container">
        <button
          className="nav-control-btn"
          onClick={() => setShowMenu(!showMenu)}
          title="More options"
        >
          <MoreVertical className="w-5 h-5" />
        </button>

        {showMenu && (
          <>
            <div
              className="nav-control-menu-backdrop"
              onClick={() => setShowMenu(false)}
            />
            <div className="nav-control-menu">
              <button
                className="nav-control-menu-item"
                onClick={() => {
                  // TODO: Implement report hazard
                  setShowMenu(false);
                }}
              >
                <Flag className="w-4 h-4" />
                Report Hazard
              </button>
              <button
                className="nav-control-menu-item"
                onClick={() => {
                  // TODO: Implement route overview
                  setShowMenu(false);
                }}
              >
                <AlertCircle className="w-4 h-4" />
                Route Overview
              </button>
            </div>
          </>
        )}
      </div>

      {/* Exit Navigation */}
      <button
        className="nav-control-btn nav-control-btn-exit"
        onClick={onExit}
        title="End navigation"
      >
        <X className="w-5 h-5" />
        <span className="nav-control-label">Exit</span>
      </button>
    </div>
  );
}
