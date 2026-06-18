import axios from 'axios';
import { RideRequest, RidePrediction, VehicleRecommendation, SurgeRecommendation } from '../types';

// Backend base URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: { 'Content-Type': 'application/json' },
});

// Vehicle types from database
export const VEHICLE_TYPES = [
    { id: 'Alphard', name: 'Alphard', price: 78000, description: 'Premium 6-seater SUV', eta: '6min', icon: '🚐' },
    { id: 'HRV', name: 'HRV', price: 65000, description: 'Comfortable 5-seater SUV', eta: '4min', icon: '🚙' },
    { id: 'Go Sedan', name: 'Go Sedan', price: 52000, description: 'Affordable 4-seater sedan', eta: '4min', icon: '🚗' },
    { id: 'Innova', name: 'Innova', price: 58000, description: 'Spacious 7-seater MPV', eta: '5min', icon: '🚐' },
    { id: 'Premier Sedan', name: 'Premier Sedan', price: 68000, description: 'Premium 4-seater sedan', eta: '5min', icon: '🚘' },
    { id: 'Brio', name: 'Brio', price: 45000, description: 'Compact 4-seater', eta: '3min', icon: '🚗' },
    { id: 'Terios', name: 'Terios', price: 55000, description: 'Compact 5-seater SUV', eta: '4min', icon: '🚙' },
];

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

    // Request ride (book)
    requestRide: async (rideRequest: any) => {
        const response = await apiClient.post('/api/rides/book', rideRequest);
        return response.data;
    },

    // Match driver to ride
    matchDriver: async (rideId: string) => {
        const response = await apiClient.post(`/api/rides/${rideId}/match-driver`);
        return response.data;
    },

    // Get ride status
    getRideStatus: async (rideId: string) => {
        const response = await apiClient.get(`/api/rides/${rideId}/status`);
        return response.data;
    },

    // Complete ride
    completeRide: async (rideId: string) => {
        const response = await apiClient.post(`/api/rides/${rideId}/complete`);
        return response.data;
    },

    // Cancel ride
    cancelRide: async (rideId: string) => {
        const response = await apiClient.post(`/api/rides/${rideId}/cancel`);
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
        const response = await apiClient.get(`/api/rides/stats`);
        return response.data;
    },

    // LLM Chat
    llmChat: async (messages: any[], userId: string = 'user123') => {
        const response = await apiClient.post('/api/llm/chat', {
            user_id: userId,
            messages,
            temperature: 0.3,
        });
        return response.data;
    },

    // LLM Route Recommendation
    llmRecommendRoute: async (query: string) => {
        const response = await apiClient.post('/api/llm/recommend-route', { query });
        return response.data;
    },
};

export default api;