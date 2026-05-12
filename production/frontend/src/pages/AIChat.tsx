import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Bot, Zap, MapPin, DollarSign } from 'lucide-react';

type Msg = { id: number; role: 'user' | 'ai'; text: string; ts: Date };

const SUGGESTIONS = ['Book ride to SCBD', 'Fare to Kemang?', 'Show my history', 'Find nearest driver'];

const AI: Record<string, string> = {
  default: "Hello! I'm GoRide AI Assistant. I can help you book rides, check fares, find drivers, and provide route recommendations. How can I assist you today?",
  book: "🚗 I found **3 nearby drivers** for you. Best option: **GoRide AI** — AI-optimized route, estimated **Rp 35,000**, arriving in **2 minutes**.\n\nShall I confirm the booking?",
  fare: "💰 Fare estimates to Kemang:\n\n• GoX Economy — Rp 28,000 (16 min)\n• GoRide AI — Rp 35,000 (12 min) ✓ Recommended\n• GoCar — Rp 52,000 (15 min)\n\nGoRide AI takes HR Rasuna Said today to avoid Sudirman jam.",
  history: "📋 Your recent rides:\n\n1. Sudirman → Senayan · Rp 45K · ⭐ 5.0\n2. SCBD → Kemang · Rp 62K · ⭐ 4.0\n3. GI → Kemang · Rp 62K · ⭐ 5.0\n\nTotal this month: **Rp 420,000** across 12 rides.",
  driver: "📍 **14 drivers** available near you!\n\nNearest: **Ahmad R.** — 2 min away · ⭐ 4.9\n\nWould you like me to book him?",
};

function getReply(text: string): string {
  const t = text.toLowerCase();
  if (t.includes('book') || t.includes('ride') || t.includes('scbd')) return AI.book;
  if (t.includes('fare') || t.includes('price') || t.includes('kemang')) return AI.fare;
  if (t.includes('history') || t.includes('past')) return AI.history;
  if (t.includes('driver') || t.includes('nearest')) return AI.driver;
  return AI.default;
}

export const AIChat: React.FC = () => {
  const [messages, setMessages] = useState<Msg[]>([{ id: 1, role: 'ai', text: AI.default, ts: new Date() }]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, typing]);

  const send = (text?: string) => {
    const content = text || input.trim();
    if (!content) return;
    setInput('');
    setMessages(p => [...p, { id: Date.now(), role: 'user', text: content, ts: new Date() }]);
    setTyping(true);
    setTimeout(() => {
      setTyping(false);
      setMessages(p => [...p, { id: Date.now() + 1, role: 'ai', text: getReply(content), ts: new Date() }]);
    }, 1200 + Math.random() * 600);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] md:h-[calc(100vh-5rem)] bg-slate-100">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 md:px-8 py-4 bg-white border-b border-slate-200 shadow-sm">
        <div className="w-11 h-11 rounded-2xl bg-blue-700 flex items-center justify-center shadow-brand">
          <Bot size={20} className="text-white" />
        </div>
        <div>
          <p className="text-slate-800 font-bold">GoRide AI Assistant</p>
          <div className="flex items-center gap-1.5">
            <span className="live-dot" />
            <span className="text-slate-400 text-xs">Online · Responds instantly</span>
          </div>
        </div>
        <div className="ml-auto badge-blue"><Zap size={10} />AI Powered</div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 md:px-8 py-4 space-y-4">
        {/* Quick suggestions */}
        {messages.length === 1 && (
          <div className="grid grid-cols-2 gap-2 mb-2">
            {SUGGESTIONS.map((s, i) => (
              <motion.button key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}
                onClick={() => send(s)} className="card p-3 text-left text-slate-500 text-xs hover:shadow-card-hover hover:text-blue-700 transition-all border border-slate-200">
                {s}
              </motion.button>
            ))}
          </div>
        )}

        <AnimatePresence>
          {messages.map(msg => (
            <motion.div key={msg.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              {msg.role === 'ai' && (
                <div className="w-8 h-8 rounded-xl bg-blue-700 flex items-center justify-center flex-shrink-0 mt-1 shadow-brand">
                  <Bot size={14} className="text-white" />
                </div>
              )}
              <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-line ${
                msg.role === 'user'
                  ? 'bg-blue-700 text-white rounded-tr-sm shadow-brand'
                  : 'bg-white border border-slate-100 text-slate-700 rounded-tl-sm shadow-card'
              }`}>
                {msg.text}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {typing && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
            <div className="w-8 h-8 rounded-xl bg-blue-700 flex items-center justify-center flex-shrink-0 shadow-brand">
              <Bot size={14} className="text-white" />
            </div>
            <div className="bg-white border border-slate-100 px-4 py-3 rounded-2xl rounded-tl-sm shadow-card flex items-center gap-1.5">
              {[0,1,2].map(i => <div key={i} className="w-2 h-2 rounded-full bg-blue-300 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />)}
            </div>
          </motion.div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 md:px-8 py-4 bg-white border-t border-slate-200">
        <div className="flex gap-3 items-end">
          <textarea value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder="Ask about rides, fares, drivers..." rows={1}
            className="flex-1 input-base resize-none" />
          <button onClick={() => send()} disabled={!input.trim()}
            className="w-12 h-12 btn-brand rounded-2xl p-0 flex items-center justify-center flex-shrink-0 disabled:opacity-40">
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};
