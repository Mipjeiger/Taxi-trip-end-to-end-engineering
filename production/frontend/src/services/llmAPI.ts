import apiClient from "./api";

export interface ChatMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
}

export const llmAPI = {
    chat: async (messages: ChatMessage[], temperature: number = 0.7) => {
        const response = await apiClient.post('/api/llm/chat', { messages, temperature });
        return response.data.response;
    },
    recommendRoute: async (query: string, context?: any) => {
        const response = await apiClient.post('/api//llm/recommend-route', { query, context });
        return response.data;
    },
    askRoute: async (question: string, routeContext?: any) => {
        const response = await apiClient.post('/api/llm/ask-route', { question, routeContext });
        return response.data.answer;
    }
}
