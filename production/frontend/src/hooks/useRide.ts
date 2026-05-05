import { useState } from 'react';
import { api } from '../services/api';

interface Ride {
  id: string;
  pickup_location: string;
  drop_location: string;
  vehicle_type: string;
  price: number;
  estimated_time_min: number;
  status: string;
}

interface RideRequest {
  userId: string;
  pickupLat: number;
  pickupLng: number;
  dropoffLat: number;
  dropoffLng: number;
}

export const useRide = () => {
  const [rides, setRides] = useState<Ride[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requestRide = async (params: RideRequest) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.requestRide(params);
      // Add the new ride to the list
      setRides(prev => [response, ...prev]);
      return response;
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const fetchRideHistory = async (userId: string) => {
    setLoading(true);
    try {
      const history = await api.getRideHistory(userId);
      setRides(history);
      return history;
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return {
    rides,
    loading,
    error,
    requestRide,
    fetchRideHistory,
  };
};