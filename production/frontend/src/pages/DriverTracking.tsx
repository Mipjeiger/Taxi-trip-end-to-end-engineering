import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { MapPin, Phone, MessageSquare, Shield, Clock, Navigation, AlertCircle } from 'lucide-react';

const STEPS = [
  { key: 'matched', label: 'Driver matched', done: true },
  { key: 'pickup', label: 'Driver en route to you', done: true },
  { key: 'arrived', label: 'Driver arrived', done: false, active: true },
  { key: 'in_ride', label: 'In ride', done: false },
  { key: 'completed', label: 'Arrived at destination', done: false },
];

export const DriverTracking: React.FC = () => {
  const [eta, setEta] = useState(3);
  const [driverX, setDriverX] = useState(22);
  const [driverY, setDriverY] = useState(74);

  useEffect(() => {
    const id = setInterval(() => {
      setDriverX(p => Math.min(p + 1.2, 60));
      setDriverY(p => Math.max(p - 0.8, 40));
      setEta(p => Math.max(0, p - 1));
    }, 2200);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="min-h-full bg-slate-100 pb-28 md:pb-8 flex flex-col">
      {/* Map Pane */}
      <div className="relative flex-1 min-h-[55vh] bg-blue-950 overflow-hidden">
        {/* Map grid */}
        <div className="absolute inset-0" style={{
          backgroundImage: `linear-gradient(rgba(96,165,250,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(96,165,250,0.07) 1px, transparent 1px)`,
          backgroundSize: '28px 28px'
        }} />

        {/* Roads */}
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
          <line x1="0" y1="50" x2="100" y2="50" stroke="rgba(148,163,184,0.1)" strokeWidth="1.2" />
          <line x1="50" y1="0" x2="50" y2="100" stroke="rgba(148,163,184,0.1)" strokeWidth="1.2" />
          <line x1="0" y1="25" x2="100" y2="25" stroke="rgba(148,163,184,0.06)" strokeWidth="0.7" />
          <line x1="0" y1="75" x2="100" y2="75" stroke="rgba(148,163,184,0.06)" strokeWidth="0.7" />
          <line x1="25" y1="0" x2="25" y2="100" stroke="rgba(148,163,184,0.06)" strokeWidth="0.7" />
          <line x1="75" y1="0" x2="75" y2="100" stroke="rgba(148,163,184,0.06)" strokeWidth="0.7" />
          {/* Route line */}
          <line x1="22" y1="74" x2="72" y2="28" stroke="#3B82F6" strokeWidth="0.8" strokeDasharray="3 2" opacity="0.7" />
        </svg>

        {/* Driver (animated) */}
        <motion.div
          animate={{ left: `${driverX}%`, top: `${driverY}%` }}
          transition={{ duration: 2, ease: 'linear' }}
          className="absolute"
        >
          <div className="relative -translate-x-1/2 -translate-y-1/2">
            <div className="absolute inset-0 w-12 h-12 -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-500/20 ring-pulse" />
            <div className="w-10 h-10 rounded-full bg-white border-2 border-blue-600 shadow-brand flex items-center justify-center text-lg shadow-lg">🚗</div>
          </div>
        </motion.div>

        {/* Destination pin */}
        <div className="absolute" style={{ left: '70%', top: '26%' }}>
          <div className="flex flex-col items-center -translate-x-1/2">
            <div className="w-9 h-9 rounded-full bg-blue-700 border-2 border-white shadow-brand flex items-center justify-center">
              <MapPin size={14} className="text-white" />
            </div>
            <div className="w-0.5 h-4 bg-blue-700" />
            <div className="w-1.5 h-1.5 rounded-full bg-blue-700" />
          </div>
        </div>

        {/* You pin */}
        <div className="absolute" style={{ left: '18%', top: '74%' }}>
          <div className="w-8 h-8 rounded-full bg-white border-3 border-black flex items-center justify-center shadow-lg text-[10px] font-bold text-slate-800 -translate-x-1/2 -translate-y-1/2">You</div>
        </div>

        {/* ETA card */}
        <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-white rounded-2xl px-6 py-3 shadow-card-hover text-center">
          <p className="text-blue-700 font-black text-3xl">{eta} min</p>
          <p className="text-slate-400 text-xs font-medium">driver arriving</p>
        </div>

        {/* Zoom controls */}
        <div className="absolute right-4 bottom-20 flex flex-col gap-1">
          {['+', '-'].map(z => (
            <button key={z} className="w-9 h-9 rounded-xl bg-white shadow-card flex items-center justify-center text-slate-600 font-bold hover:bg-slate-50 transition-all text-base">
              {z}
            </button>
          ))}
        </div>

        <div className="absolute bottom-0 inset-x-0 h-12 bg-gradient-to-t from-slate-100 to-transparent" />
      </div>

      {/* Driver Info Sheet */}
      <div className="px-4 md:px-8 py-5 space-y-3">
        {/* Driver card */}
        <div className="card p-4 flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center text-3xl">👨</div>
          <div className="flex-1">
            <p className="text-slate-800 font-bold text-base">Ahmad Rizki</p>
            <p className="text-slate-400 text-xs">Honda Beat ·  <span className="text-slate-600 font-medium">B 1234 XY</span></p>
            <div className="flex items-center gap-3 mt-1">
              <span className="badge-blue">⭐ 4.9</span>
              <span className="text-slate-400 text-xs">1,240 trips</span>
              <span className="badge-green"><Shield size={10} /> Verified</span>
            </div>
          </div>
          <div className="flex gap-2">
            <button className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 hover:bg-blue-100 transition-all">
              <Phone size={16} />
            </button>
            <button className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 hover:bg-blue-100 transition-all">
              <MessageSquare size={16} />
            </button>
          </div>
        </div>

        {/* Route progress */}
        <div className="card p-4">
          <p className="section-label mb-3">Trip progress</p>
          <div className="space-y-2.5">
            {STEPS.map((s, i) => (
              <div key={s.key} className="flex items-center gap-3">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 border-2 ${
                  s.done ? 'bg-emerald-500 border-emerald-500' :
                  s.active ? 'border-blue-500 bg-blue-50 animate-pulse' :
                  'border-slate-200 bg-white'
                }`}>
                  {s.done && <span className="text-white text-[9px] font-bold">✓</span>}
                  {s.active && <div className="w-2 h-2 rounded-full bg-blue-500" />}
                </div>
                <span className={`text-sm ${s.done ? 'text-slate-400 line-through' : s.active ? 'text-blue-700 font-semibold' : 'text-slate-400'}`}>{s.label}</span>
                {s.active && <span className="ml-auto badge-blue">Now</span>}
              </div>
            ))}
          </div>
        </div>

        {/* Trip details */}
        <div className="card p-4 grid grid-cols-3 gap-4 text-center">
          {[
            { icon: Clock, label: 'Duration', value: '12 min', color: 'text-blue-600', bg: 'bg-blue-50' },
            { icon: Navigation, label: 'Distance', value: '6.4 km', color: 'text-sky-600', bg: 'bg-sky-50' },
            { icon: MapPin, label: 'Est. Fare', value: 'Rp 35K', color: 'text-emerald-600', bg: 'bg-emerald-50' },
          ].map(d => (
            <div key={d.label}>
              <div className={`w-8 h-8 rounded-xl ${d.bg} flex items-center justify-center mx-auto mb-2`}>
                <d.icon size={15} className={d.color} />
              </div>
              <p className="text-slate-800 font-bold text-sm">{d.value}</p>
              <p className="text-slate-400 text-xs">{d.label}</p>
            </div>
          ))}
        </div>

        {/* SOS */}
        <button className="w-full flex items-center justify-center gap-2 card p-3 text-red-500 border-red-100 hover:bg-red-50 transition-all text-sm font-semibold">
          <AlertCircle size={15} />
          Emergency / SOS
        </button>
      </div>
    </div>
  );
};
