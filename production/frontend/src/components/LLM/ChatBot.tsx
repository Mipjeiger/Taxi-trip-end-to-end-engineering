import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, X } from 'lucide-react';
import llmAPI, { ChatMessage } from '../../services/llmAPI';  // Use default import
import ReactMarkdown from 'react-markdown';
import './css/Chatbot.css';

interface ChatBotProps {
  isOpen: boolean;
  onClose: () => void;
  routeContext?: any;
  priceContext?: any;
}

const MAX_MESSAGES = 50;
const API_TIMEOUT = 30000; // 30 seconds

export const ChatBot: React.FC<ChatBotProps> = ({
  isOpen,
  onClose,
  routeContext,
  priceContext,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        'Hi! I am your ride assistant. I can help you with route recommendations, traffic info, or booking tips. Ask me anything!',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userInput = input.trim();
    const userMsg: ChatMessage = { role: 'user', content: userInput };
    
    setInput('');
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    // Set timeout for API call
    timeoutRef.current = setTimeout(() => {
      setLoading(false);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '⏱️ Request timed out. Please try again.',
        },
      ]);
    }, API_TIMEOUT);

    try {
      let response = '';

      // LLM queries based on context and keywords
      if (
        routeContext &&
        (userInput.toLowerCase().includes('route') ||
          userInput.toLowerCase().includes('trip') ||
          userInput.toLowerCase().includes('direction') ||
          userInput.toLowerCase().includes('fast') ||
          userInput.toLowerCase().includes('best'))
      ) {
        response = await llmAPI.askRoute(userInput, routeContext);
      }
      // Handle price-specific queries
      else if (
        priceContext &&
        (userInput.toLowerCase().includes('price') ||
          userInput.toLowerCase().includes('cost') ||
          userInput.toLowerCase().includes('fare') ||
          userInput.toLowerCase().includes('how much'))
      ) {
        response = await llmAPI.askPrice(userInput, priceContext);
      }
      // Default: general chat with conversation history
      else {
        const conversation: ChatMessage[] = [...messages, userMsg];
        response = await llmAPI.chat(conversation);
      }

      // Clear timeout and update messages with response
      clearTimeout(timeoutRef.current);
      setLoading(false);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response || 'I didn\'t get a response. Please try again.',
        },
      ]);
    } catch (error: any) {
      clearTimeout(timeoutRef.current);
      setLoading(false);

      const errorMsg =
        error?.response?.status === 429
          ? '⚠️ Too many requests. Please wait a moment and try again.'
          : error?.response?.status === 401
          ? '🔐 Authentication failed. Please check your API key.'
          : error?.message?.includes('timeout')
          ? '⏱️ Request took too long. Please try again.'
          : error?.message || '❌ Sorry, something went wrong. Please try again.';

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: errorMsg,
        },
      ]);

      console.error('Chat error:', error);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed bottom-4 right-4 w-96 h-[500px] bg-white rounded-2xl shadow-2xl flex flex-col z-50 border">
      {/* Header */}
      <div className="flex justify-between items-center p-4 border-b bg-green-500 text-white rounded-t-2xl">
        <div className="flex items-center gap-2">
          <Bot size={20} />
          <span className="font-semibold">Trip ChatBot</span>
          {loading && <span className="ml-2 animate-pulse">●</span>}
        </div>
        <button
          onClick={onClose}
          className="hover:bg-green-600 p-1 rounded transition"
          aria-label="Close chat"
        >
          <X size={20} />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                msg.role === 'user'
                  ? 'bg-green-500 text-white rounded-br-none'
                  : 'bg-gray-100 text-gray-800 rounded-bl-none'
              }`}
            >
              {msg.role === 'assistant' ? (
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
              ) : (
                <p className="text-sm">{msg.content}</p>
              )}
            </div>
          </div>
        ))}

        {/* Typing Indicator */}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-3 rounded-bl-none">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t bg-gray-50">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !loading && sendMessage()}
            placeholder="Ask about routes, traffic, or places..."
            className="flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
            disabled={loading}
            aria-label="Chat message input"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="bg-green-500 text-white p-2 rounded-lg hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
            aria-label="Send message"
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatBot;