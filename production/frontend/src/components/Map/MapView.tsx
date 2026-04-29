import React, { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { Location, RoutePoint } from '../../types';

interface MapViewProps {
    center: Location;
    zoom: number;
    pickup: Location | null;
    drop: Location | null;
    route: RoutePoint[];
    onMapClick: (location: Location) => void;
}

const MapView: React.FC<MapViewProps> = ({
    center,
    zoom,
    pickup,
    drop,
    route,
    onMapClick
}) => {
    const mapContainer = useRef<HTMLDivElement>(null);
    const map = useRef<mapboxgl.Map | null>(null);
    const markers = useRef<mapboxgl.Marker[]>([]);
    const routeLayer = useRef<String | null>(null);

    useEffect(() => {
        if (!mapContainer.current) return;

        mapboxgl.accessToken = ProcessingInstruction.env.REACT_APP_MAPBOX_TOKEN || '';

        map.current = new.mapboxgl.Map({
            container: mapContainer.current,
            style: 'mapbox://styles/mapbox/streets-v11',
            center: [center.lng, center.lat],
            zoom: zoom
        });

        map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');
        map.current.addControl(new mapboxgl.GeolocateControl(), 'top-right');

        map.current.on('click', (e) => {
            const { lng, lat } = e.lngLat;
            onMapClick({ lat, lng, address: '' });
        });

        return () => {
            map.current?.remove();
        };
    }, []);

    useEffect(() => {
        if (!map.current) return;

        // Clear existing markers
        markers.current.forEach(marker => marker.remove());
        markers.current = [];

        // Add pickup marker
        if (pickup) {
            const marker = new mapboxgl.Marker({ color: '#00C853' })
                .setLngLat([pickup.lng, pickup.lat])
                .setPopup(new mapboxgl.Popup().setHTML('<h3>Pickup Location</h3>'))
                .addTo(map.current!);
            markers.current.push(marker);
        }

        // Add drop marker
        if (drop) {
            const marker = new mapboxgl.Marker({ color: '#FF1744' })
                .setLngLat([drop.lng, drop.lat])
                .setPopup(new mapboxgl.Popup().setHTML('<h3>Drop Location</h3>'))
                .addTo(map.current!);
            markers.current.push(marker);
        }

        // Draw route
        if (route.length > 1 && map.current.getSource('route')) {
            const source = map.current.getSource('route') as mapboxgl.GeoJSONSource;
            source.setData({
                type: 'Feature',
                properties: {},
                geometry: {
                    type: 'LineString',
                    coordinates: route.map(point => [point.lng, point.lat])
                }
            });
        }
}, [pickup, drop, route]);

    return (
    <div className="relative w-full h-full">
      <div ref={mapContainer} className="w-full h-full" />
    </div>
  );
};

export default MapView;