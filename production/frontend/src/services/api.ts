import axios from 'axios';
import { RideRequest, RidePrediction, VehicleRecommendation, SurgeRecommendation } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: { 'Content-Type': 'application/json' },
});

export const api = {
    // Ride prediction
    predictRoute: async (request: RideRequest): Promise<RidePrediction> => {
        const response = await apiClient.post('/api/predict/route', request);
        return response.data;
    },

    // Vehicle recommendation
    recommendVehicle: async (userId: string, context: any): Promise<RidePrediction> => {
        const response = await apiClient.post('/api/recommend/vehicle', { userId, context });
        return response.data;
    },

    // Surge recommendation
    getSurgeRecommendation: async (location: string, currentSurge: number): Promise<SurgeRecommendation> => {
        const response = await apiClient.get(`/api/recommend/surge/${location}`, {
            params: { current_surge: currentSurge }
        });
        return response.data;
    },

    // Request ride
    requestRide: async (rideRequest: any) => {
        const response = await apiClient.post('/api/ride/request', rideRequest);
        return response.data;
    },

    // Ride history
    getRideHistory: async (userId: string) => {
        const response = await apiClient.get(`/api/rides/history/${userId}`);
        return response.data;
    }
};