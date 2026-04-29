export interface Location {
    lat: number;
    lng: number;
    address: string;
}

export interface RideRequest {
    pickup_location: string;
    drop_location: string;
    vehicle_type: 'Car' | 'Bike' | 'Auto';
    hour?: number;
    day_of_week?: string;
}

export interface RidePrediction {
    pickup_location: string;
    drop_location: string;
    distance_km: number;
    estimated_time_min: number;
    vtat_min: number;
    ctat_min: number;
    estimated_price_idr: number;
    average_speed_kmh: number;
    price_per_km: number;
    vehicle_type: string;
}

export interface RoutePoint {
    lat: number;
    lng: number;
    type: 'pickup' | 'drop' | 'waypoint';
}

export interface MapState {
    center: Location;
    zoom: number;
    pickup: Location | null;
    drop: Location | null;
    route: RoutePoint[];
}