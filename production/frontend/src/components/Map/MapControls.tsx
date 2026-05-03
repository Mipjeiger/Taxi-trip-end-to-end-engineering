import React from 'react';

interface MapControlsProps {
    onZoomIn: () => void;
    onZoomOut: () => void;
    onRecenter: () => void;
    onToggleHeatmap: () => void;
    heatmapEnabled: boolean;
}

export const MapControls: React.FC<MapControlsProps> = ({
    onZoomIn,
    onZoomOut,
    onRecenter,
    onToggleHeatmap,
    heatmapEnabled
}) => {
    return (
    <div className="map-controls">
      <button onClick={onZoomIn} title="Zoom in">🔍+</button>
      <button onClick={onZoomOut} title="Zoom out">🔍-</button>
      <button onClick={onRecenter} title="Recenter">🎯</button>
      <button 
        onClick={onToggleHeatmap}
        className={heatmapEnabled ? 'active' : ''}
        title="Toggle heatmap"
      >
        🔥 {heatmapEnabled ? 'On' : 'Off'}
      </button>
    </div>
  );
};