import axios from 'axios';
import { RideRequest, RidePrediction, VehicleRecommendation, SurgeRecommendation, ChurnPromo } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
    baseUrl: API_BASE_URL,
    headers: { ' Content-Type': 'application/json' },
});

export const api = {
    // Ride prediction
    predictRoute: async (request: RideRequest): Promise<RidePrediction> => {
        const response = await apiClient.post('/api/predict/route', request);
        return response.data;
    },

    // Vehicle recommendation
    recommendVehicle: async (userID: string, context: any): Promise<RidePrediction> => {
        const response = await apiClient.post('/api/recommend/vehicle', { userID, context });
        return response.data;
    },

    // Surge recommendation
    getSurgeRecommendation: async (location: string, currentSurge: number): Promise<SurgeRecommendation> => {
        const response = await apiClient.post(`/api/recommend/surge/${location}?current_surge=${currentSurge}`);
        return response.data;
    },

    // Churn promo recommendation
    getChurnPromo: async (userIDL string, features: any): Promise<ChurnPromo> => {
        const response = await apiClient.post(`/api/recommend/churn_promo/${userID}`, features);
        return response.data;
    },

    // Driver matching (simulated)
    requestRide: async (rideRequestL any) => {
        const response = await apiClient.post('/api/ride/request', rideRequest);
        return response.data;
    },

    // Ride history
    getRideHistory: async (userID: string) => {
        const response = await apiClient.get(`/api/rides/history/${userID}`);
        return response.data;
    }
};