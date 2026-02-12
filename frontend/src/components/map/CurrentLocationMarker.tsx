import { Marker } from 'react-map-gl';

interface CurrentLocationMarkerProps {
  longitude: number;
  latitude: number;
  heading: number | null;
}

export default function CurrentLocationMarker({
  longitude,
  latitude,
  heading,
}: CurrentLocationMarkerProps) {
  return (
    <Marker
      longitude={longitude}
      latitude={latitude}
      anchor="center"
    >
      <div className="current-location-marker-container">
        {/* Heading indicator (arrow) */}
        {heading !== null && (
          <div
            className="current-location-heading"
            style={{ transform: `rotate(${heading}deg)` }}
          >
            <svg
              width="32"
              height="32"
              viewBox="0 0 32 32"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M16 4L22 16H10L16 4Z"
                fill="currentColor"
                fillOpacity="0.9"
              />
            </svg>
          </div>
        )}

        {/* Accuracy circle / outer glow */}
        <div className="current-location-glow" />

        {/* Main marker dot */}
        <div className="current-location-dot">
          <div className="current-location-dot-inner" />
        </div>
      </div>
    </Marker>
  );
}
