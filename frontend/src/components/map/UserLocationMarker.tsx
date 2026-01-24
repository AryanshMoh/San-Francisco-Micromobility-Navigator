import { Marker } from 'react-map-gl';

interface UserLocationMarkerProps {
  longitude: number;
  latitude: number;
  type: 'origin' | 'destination' | 'current';
  heading?: number;
}

export default function UserLocationMarker({
  longitude,
  latitude,
  type,
  heading,
}: UserLocationMarkerProps) {
  // Different styles for different marker types
  const getMarkerStyle = () => {
    switch (type) {
      case 'origin':
        return {
          backgroundColor: '#22c55e', // Green
          borderColor: '#ffffff',
          icon: '🚀',
        };
      case 'destination':
        return {
          backgroundColor: '#ef4444', // Red
          borderColor: '#ffffff',
          icon: '📍',
        };
      case 'current':
        return {
          backgroundColor: '#3b82f6', // Blue
          borderColor: '#ffffff',
          icon: null,
        };
    }
  };

  const style = getMarkerStyle();

  return (
    <Marker longitude={longitude} latitude={latitude} anchor="center">
      <div
        className="relative flex items-center justify-center"
        style={{
          transform: heading !== undefined ? `rotate(${heading}deg)` : undefined,
        }}
      >
        {/* Outer ring / pulse animation for current location */}
        {type === 'current' && (
          <div
            className="absolute w-10 h-10 rounded-full animate-ping opacity-30"
            style={{ backgroundColor: style.backgroundColor }}
          />
        )}

        {/* Main marker */}
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center text-white shadow-lg"
          style={{
            backgroundColor: style.backgroundColor,
            border: `3px solid ${style.borderColor}`,
          }}
        >
          {style.icon && <span className="text-sm">{style.icon}</span>}
        </div>

        {/* Direction indicator for current location */}
        {type === 'current' && heading !== undefined && (
          <div
            className="absolute -top-1 w-0 h-0"
            style={{
              borderLeft: '6px solid transparent',
              borderRight: '6px solid transparent',
              borderBottom: `10px solid ${style.backgroundColor}`,
            }}
          />
        )}
      </div>
    </Marker>
  );
}
