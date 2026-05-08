import { apiClient } from "./api";

export interface ChatMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
}

export interface LLMResponse {
    response: string;
    status: 'success' | 'error';
    timestamp?: string;
}

export interface RouteRecommendation {
    route: string;
    estimated_time: number;
    description: string;
}

export const llmAPI = {
    // Chat endpoint - send messages and get response
    chat: async (messages: ChatMessage[], temperature: number = 0.7): Promise<string> => {
        try {
            const response = await apiClient.post('/api/llm/chat', {
                messages,
                temperature,
            });
            // Handle both direct string response and nested response object
            return response.data.response || response.data;
        } catch (error) {
            console.error('Chat API error:', error);
            throw error;
        }
    },

    // Route recommendation - get recommended route from LLM
    recommendRoute: async (query: string, context?: any): Promise<RouteRecommendation> => {
        try {
            const response = await apiClient.post('/api/llm/recommend-route', {
                query,
                context,
            });
            return response.data;
        } catch (error) {
            console.error('Route recommendation error:', error);
            throw error;
        }
    },

    // Ask about specific route
    askRoute: async (question: string, routeContext?: any): Promise<string> => {
        try {
            const response = await apiClient.post('/api/llm/ask-route', {
                question,
                route_context: routeContext,
            });
            // Handle both answer and response fields
            return response.data.answer || response.data.response || response.data;
        } catch (error) {
            console.error('Ask route error:', error);
            throw error;
        }
    },

    // Ask about price
    askPrice: async (question: string, priceContext?: any): Promise<string> => {
        try {
            const response = await apiClient.post('/api/llm/ask-price', {
                question,
                price_context: priceContext,
            });
            // Handle both answer and response fields
            return response.data.answer || response.data.response || response.data;
        } catch (error) {
            console.error('Ask price error:', error);
            throw error;
        }
    },
};

export default llmAPI;