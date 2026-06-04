import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Bot, Zap } from 'lucide-react';
import llmAPI, { ChatMessage } from '../services/llmAPI';

type Msg = { id: number; role: 'user' | 'ai'; text: string; ts: Date };

const SUGGESTIONS = ['Best route from Pasar Baru to Cilandak Timur?',
                    'Berapa tarif ke Kelapa Gading Barat?',
                    'Jalur alternatif menghindari macet?',
                    'Find nearest driver',];

const GREETING = "Hello! I'm TaxiRide AI Assistant 🤖. I can help you book rides, check fares, find drivers, and provide route recommendations. How can I assist you today?";

export const AIChat: React.FC = () => {
  const [messages, setMessages] = useState<Msg[]>([
    { id: 1, role: 'ai', text: GREETING, ts: new Date() },
  ]);
  // Conversation history sent to the API (excludes greeting)
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, typing]);

  const send = async (text?: string) => {
    const content = (text || input).trim();
    if (!content || typing) return;

    setInput('');

    // Add user message to display
    setMessages(prev => [
      ...prev,
      { id: Date.now(), role: 'user', text: content, ts: new Date() },
    ]);
    setTyping(true);

    // Build updated history including this new user message
    const userMsg: ChatMessage = { role: 'user', content };
    const updatedHistory: ChatMessage[] = [...history, userMsg];
    
    try {
      const data = await llmAPI.chat(
        updatedHistory,
        0.7,
        "guest-user",
        sessionId
      );

      // Persist session for conversation continuity
      if (!sessionId && data.session_id) {
        setSessionId(data.session_id);
      }

      const assistantMsg: ChatMessage = { role: 'assistant', content: data.response };

      // keep last 20 messages in history to avoid token overflow
     setHistory([...updatedHistory, assistantMsg].slice(-20));
     
     setTyping(false);
     setMessages(prev => [
       ...prev,
       { id: Date.now() + 1, role: 'ai', text: data.response, ts: new Date() },
     ]);
    } catch (error: any) {
      setTyping(false);

      const errText = 
        error?.response?.status === 429
          ? '⚠️ Too many requests. Please wait a moment.'
          : error?.response?.status === 500
          ? '❌ Server error. Please try again.'
          : error?.message?.includes('timeout')
          ? '⏱️ Request timed out. Please try again.'
          : '❌ Sorry, something went wrong. Please try again.';

      setMessages(prev => [
        ...prev,
        { id: Date.now() + 1, role: 'ai', text: errText, ts: new Date() },
      ]);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] md:h-[calc(100vh-5rem)] bg-slate-100">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 md:px-8 py-4 bg-white border-b border-slate-200 shadow-sm">
        <div className="w-11 h-11 rounded-2xl bg-blue-700 flex items-center justify-center shadow-brand">
          <Bot size={20} className="text-white" />
        </div>
        <div>
          <p className="text-slate-800 font-bold">TaxiRide AI Assistant</p>
          <div className="flex items-center gap-1.5">
            <span className="live-dot" />
            <span className="text-slate-400 text-xs">Online · Responds instantly</span>
          </div>
        </div>
        <div className="ml-auto badge-blue flex items-center gap-1">
          <Zap size={10} /> AI Powered
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 md:px-8 py-4 space-y-4">
        {/* Quick suggestions — only show before first user message */}
        {messages.length === 1 && (
          <div className="grid grid-cols-2 gap-2 mb-2">
            {SUGGESTIONS.map((s, i) => (
              <motion.button
                key={i}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.07 }}
                onClick={() => send(s)}
                className="card p-3 text-left text-slate-500 text-xs hover:shadow-card-hover hover:text-blue-700 transition-all border border-slate-200"
              >
                {s}
              </motion.button>
            ))}
          </div>
        )}

        <AnimatePresence>
          {messages.map(msg => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
            >
              {msg.role === 'ai' && (
                <div className="w-8 h-8 rounded-xl bg-blue-700 flex items-center justify-center flex-shrink-0 mt-1 shadow-brand">
                  <Bot size={14} className="text-white" />
                </div>
              )}
              <div
                className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-line ${
                  msg.role === 'user'
                    ? 'bg-blue-700 text-white rounded-tr-sm shadow-brand'
                    : 'bg-white border border-slate-100 text-slate-700 rounded-tl-sm shadow-card'
                }`}
              >
                {msg.text}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Typing indicator */}
        {typing && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
            <div className="w-8 h-8 rounded-xl bg-blue-700 flex items-center justify-center flex-shrink-0 shadow-brand">
              <Bot size={14} className="text-white" />
            </div>
            <div className="bg-white border border-slate-100 px-4 py-3 rounded-2xl rounded-tl-sm shadow-card flex items-center gap-1.5">
              {[0, 1, 2].map(i => (
                <div
                  key={i}
                  className="w-2 h-2 rounded-full bg-blue-300 animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          </motion.div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 md:px-8 py-4 bg-white border-t border-slate-200">
        <div className="flex gap-3 items-end">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="Ask about rides, fares, drivers..."
            rows={1}
            className="flex-1 input-base resize-none"
            disabled={typing}
          />
          <button
            onClick={() => send()}
            disabled={!input.trim() || typing}
            className="w-12 h-12 btn-brand rounded-2xl p-0 flex items-center justify-center flex-shrink-0 disabled:opacity-40"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default AIChat;