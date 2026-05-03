import { useState, useCallback } from 'react';

interface MapState {
  center: { lat: number; lng: number };
  zoom: number;
  heatmapEnabled: boolean;
}

export const useMap = (initialCenter = { lat: -6.2088, lng: 106.8456 }) => {
  const [state, setState] = useState<MapState>({
    center: initialCenter,
    zoom: 13,
    heatmapEnabled: false,
  });

  const zoomIn = useCallback(() => {
    setState(prev => ({ ...prev, zoom: Math.min(prev.zoom + 1, 20) }));
  }, []);

  const zoomOut = useCallback(() => {
    setState(prev => ({ ...prev, zoom: Math.max(prev.zoom - 1, 1) }));
  }, []);

  const setCenter = useCallback((lat: number, lng: number) => {
    setState(prev => ({ ...prev, center: { lat, lng } }));
  }, []);

  const toggleHeatmap = useCallback(() => {
    setState(prev => ({ ...prev, heatmapEnabled: !prev.heatmapEnabled }));
  }, []);

  return { ...state, zoomIn, zoomOut, setCenter, toggleHeatmap };
};