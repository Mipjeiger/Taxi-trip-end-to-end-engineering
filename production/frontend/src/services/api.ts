import axios from 'axios';
import { RideRequest, RidePrediction, VehicleRecommendation, SurgeRecommendation } from '../types';

// Backend base URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: { 'Content-Type': 'application/json' },
});

export const api = {
    // Ride prediction
    predictRoute: async (request: RideRequest): Promise<RidePrediction> => {
        const response = await apiClient.post('/api/prediction/predict_ride', request);
        return response.data;
    },

    // Vehicle recommendation
    recommendVehicle: async (userId: string, context: any): Promise<RidePrediction> => {
        const response = await apiClient.post('/api/recommendations/vehicle', { userId, context });
        return response.data;
    },

    // Surge recommendation
    getSurgeRecommendation: async (location: string, currentSurge: number): Promise<SurgeRecommendation> => {
        const response = await apiClient.get(`/api/recommendations/surge/${location}`, {
            params: { current_surge: currentSurge }
        });
        return response.data;
    },

    // Request ride
    requestRide: async (rideRequest: any) => {
        const response = await apiClient.post('/api/rides/request', rideRequest);
        return response.data;
    },

    // Ride history
    getRideHistory: async (userId: string, limit: number = 150) => {
        const response = await apiClient.get(`/api/rides/history/${userId}?limit=${limit}`);
        return response.data;
    },

    // Get ride details
    getRideDetails: async (rideId: string) => {
        const response = await apiClient.get(`/api/rides/${rideId}`);
        return response.data;
    },

    // Ride stats
    getRideStats: async () => {
        const response = await apiClient.get(`/api/analytics/stats`);
        return response.data;
    }
};

export default api;