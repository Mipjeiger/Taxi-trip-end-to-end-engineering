import React, { useEffect, useRef } from 'react';
import { MapControls } from './MapControls';

interface Location {
    lat: number;
    lng: number;
}

interface RouteMapProps {
    pickup: Location;
    dropoff: Location;
    route?: Location[];
    onMapLoad?: () => void;
}

export const RouteMap: React.FC<RouteMapProps> = ({ pickup, dropoff, route, onMapLoad }) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = React.useState(13);
  const [heatmapEnabled, setHeatmapEnabled] = React.useState(false);

  useEffect(() => {
      // Initialize map
      if (mapRef.current) {
          onMapLoad?.(); // Use Google Maps, Mapbox, or Leaflet to render the map
      }
  }, [onMapLoad]);

  return (
  <div className="route-map-container">
    <div 
      ref={mapRef} 
      className="map" 
      style={{ 
        height: '400px',
        background: '#e0e0e0',
        borderRadius: '8px'
      }} 
    >
      <p style={{ padding: '20px', color: '#666' }}>
        📍 Pickup: ({pickup.lat}, {pickup.lng})<br/>
        📍 Dropoff: ({dropoff.lat}, {dropoff.lng})
      </p>
    </div>
    <MapControls
      onZoomIn={() => setZoom(zoom + 1)}
      onZoomOut={() => setZoom(zoom - 1)}
      onRecenter={() => setZoom(13)}
      onToggleHeatmap={() => setHeatmapEnabled(!heatmapEnabled)}
      heatmapEnabled={heatmapEnabled}
    />
  </div>
);
};