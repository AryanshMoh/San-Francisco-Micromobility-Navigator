import { useState, useEffect } from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface SteepHillWarningProps {
  maxGradePercent: number;
  onDismiss: () => void;
}

/**
 * Popup warning displayed when a route contains steep hills (>15% grade).
 * Shows centered on the screen with the warning message and dismiss button.
 */
export default function SteepHillWarning({ maxGradePercent, onDismiss }: SteepHillWarningProps) {
  const [isVisible, setIsVisible] = useState(true);

  // Auto-dismiss after 8 seconds
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(onDismiss, 300); // Allow fade-out animation
    }, 8000);

    return () => clearTimeout(timer);
  }, [onDismiss]);

  const handleDismiss = () => {
    setIsVisible(false);
    setTimeout(onDismiss, 300);
  };

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm transition-opacity duration-300 ${
        isVisible ? 'opacity-100' : 'opacity-0 pointer-events-none'
      }`}
      onClick={handleDismiss}
    >
      <div
        className={`bg-white rounded-2xl shadow-2xl max-w-sm w-full p-6 transform transition-all duration-300 ${
          isVisible ? 'scale-100 translate-y-0' : 'scale-95 translate-y-4'
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Warning Icon */}
        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 bg-caution-100 rounded-full flex items-center justify-center">
            <AlertTriangle className="w-8 h-8 text-caution-500" />
          </div>
        </div>

        {/* Warning Text */}
        <div className="text-center">
          <h2 className="text-xl font-bold text-caution-600 mb-2">
            Warning
          </h2>
          <p className="text-2xl font-semibold text-slate-900 mb-3">
            This is a Steep Hill
          </p>
          <p className="text-sm text-slate-500 mb-1">
            Maximum grade: <span className="font-semibold text-slate-700">{maxGradePercent.toFixed(0)}%</span>
          </p>
          <p className="text-xs text-slate-400">
            Routes with grades over 15% may be challenging for micromobility vehicles.
          </p>
        </div>

        {/* Dismiss Button */}
        <button
          onClick={handleDismiss}
          className="mt-6 w-full py-3 px-4 bg-slate-900 text-white rounded-xl font-medium text-sm hover:bg-slate-800 transition-colors flex items-center justify-center gap-2"
        >
          <X className="w-4 h-4" />
          Got it
        </button>
      </div>
    </div>
  );
}
