import { useState, useCallback } from 'react';
import { api } from '../services/api';

interface RideRequest {
    userId: string;
    pickupLat: number;
    pickupLng: number;
    dropoffLat: number;
    dropoffLng: number;
}

export const useRide = () => {
    const [rides, setRides] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const requestRide = useCallback(async (rideRequest: RideRequest) => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.requestRide(request);
            setRides(prev => [...prev, response]);
            return response;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to request ride');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getRideHistory = useCallback(async (userId: string) => {
    setLoading(true);
    try {
      const response = await api.getRideHistory(userId);
      setRides(response);
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch history');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { rides, loading, error, requestRide, getRideHistory };
};