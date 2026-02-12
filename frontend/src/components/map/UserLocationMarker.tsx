import { Marker } from 'react-map-gl';
import { useCallback } from 'react';

interface UserLocationMarkerProps {
  longitude: number;
  latitude: number;
  type: 'origin' | 'destination' | 'current';
}

export default function UserLocationMarker({
  longitude,
  latitude,
  type,
}: UserLocationMarkerProps) {
  // Prevent any click from propagating to the map
  const stopPropagation = useCallback((e: React.MouseEvent | React.PointerEvent) => {
    e.stopPropagation();
    e.preventDefault();
  }, []);

  return (
    <Marker
      longitude={longitude}
      latitude={latitude}
      anchor="center"
    >
      <div
        onClick={stopPropagation}
        onMouseDown={stopPropagation}
        onPointerDown={stopPropagation}
        className={`location-marker ${type}`}
      />
    </Marker>
  );
}
