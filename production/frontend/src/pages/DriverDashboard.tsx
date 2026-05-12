import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { DollarSign, Zap, Clock, Star, TrendingUp, Car, CheckCircle } from 'lucide-react';

const earningsData = [
  { day: 'Mon', v: 180000 }, { day: 'Tue', v: 240000 }, { day: 'Wed', v: 195000 },
  { day: 'Thu', v: 310000 }, { day: 'Fri', v: 285000 }, { day: 'Sat', v: 420000 }, { day: 'Sun', v: 150000 },
];
const maxEarning = Math.max(...earningsData.map(e => e.v));

const recentTrips = [
  { id: 1, name: 'Miftah H.', route: 'Sudirman → Senayan', fare: 'Rp 45.000', t: '10 min ago' },
  { id: 2, name: 'Budi S.', route: 'SCBD → Kemang', fare: 'Rp 62.000', t: '1h ago' },
  { id: 3, name: 'Rina L.', route: 'Semanggi → Tebet', fare: 'Rp 38.000', t: '2h ago' },
];

export const DriverDashboard: React.FC = () => {
  const [online, setOnline] = useState(true);

  return (
    <div className="page-container space-y-5">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-slate-800 font-black text-2xl">Driver Dashboard</h1>
          <p className="text-slate-400 text-sm">Tuesday, 12 May 2026</p>
        </div>
        <button onClick={() => setOnline(!online)}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-sm transition-all border-2 ${online ? 'bg-emerald-50 border-emerald-300 text-emerald-700' : 'bg-slate-100 border-slate-200 text-slate-500'}`}>
          <div className={`w-2 h-2 rounded-full ${online ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
          {online ? 'Online' : 'Offline'}
        </button>
      </div>

      {/* Incoming request */}
      {online && (
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="card p-5 border-2 border-blue-400 bg-blue-50/60">
          <div className="flex items-center gap-2 mb-3">
            <span className="live-dot" />
            <span className="text-blue-700 font-bold text-sm">New Ride Request</span>
          </div>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-11 h-11 rounded-xl bg-blue-100 flex items-center justify-center text-xl">👤</div>
            <div className="flex-1">
              <p className="text-slate-800 font-bold">Andi Kusuma</p>
              <p className="text-slate-500 text-xs">Sudirman → Senayan City · 4.8 km</p>
            </div>
            <div className="text-right">
              <p className="text-blue-700 font-black text-lg">Rp 52.000</p>
              <p className="text-slate-400 text-xs">Est. fare</p>
            </div>
          </div>
          <div className="flex gap-3">
            <button className="btn-brand flex-1 h-11">Accept Ride</button>
            <button className="btn-ghost flex-1 h-11 border border-slate-200 text-sm">Decline</button>
          </div>
        </motion.div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Today's Earnings", value: 'Rp 285K', icon: DollarSign, bg: 'bg-blue-50', ic: 'text-blue-600' },
          { label: 'Trips Today', value: '8', icon: Zap, bg: 'bg-sky-50', ic: 'text-sky-500' },
          { label: 'Online', value: '5h 32m', icon: Clock, bg: 'bg-amber-50', ic: 'text-amber-500' },
        ].map((k, i) => (
          <motion.div key={k.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }} className="card p-4 text-center">
            <div className={`w-9 h-9 rounded-xl ${k.bg} flex items-center justify-center mx-auto mb-3`}>
              <k.icon size={16} className={k.ic} />
            </div>
            <p className="text-slate-800 font-black text-lg">{k.value}</p>
            <p className="text-slate-400 text-xs mt-0.5">{k.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Earnings bar chart */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-slate-700 font-bold">Weekly Earnings</h3>
          <div className="flex items-center gap-1.5 badge-green"><TrendingUp size={10} />+18% vs last week</div>
        </div>
        <div className="flex items-end justify-between gap-2 h-28">
          {earningsData.map((e, i) => {
            const h = (e.v / maxEarning) * 100;
            const today = e.day === 'Fri';
            return (
              <div key={e.day} className="flex-1 flex flex-col items-center gap-1">
                <motion.div
                  initial={{ height: 0 }} animate={{ height: `${h}%` }} transition={{ delay: i * 0.06, duration: 0.5 }}
                  className={`w-full rounded-t-lg ${today ? 'bg-blue-600 shadow-brand' : 'bg-blue-100'}`}
                />
                <span className={`text-[10px] font-medium ${today ? 'text-blue-600' : 'text-slate-400'}`}>{e.day}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Rating */}
      <div className="card p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-50 flex items-center justify-center">
            <Star size={18} className="text-amber-500" />
          </div>
          <div>
            <p className="text-slate-700 font-semibold">Driver Rating</p>
            <p className="text-slate-400 text-xs">Last 100 trips</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-slate-800 font-black text-2xl">4.93</p>
          <span className="badge-green">Excellent</span>
        </div>
      </div>

      {/* Recent Trips */}
      <div>
        <p className="section-label mb-3">Recent trips</p>
        <div className="space-y-2">
          {recentTrips.map((t, i) => (
            <motion.div key={t.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.07 }} className="card p-4 flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-blue-50 flex items-center justify-center text-base flex-shrink-0">👤</div>
              <div className="flex-1 min-w-0">
                <p className="text-slate-700 font-medium text-sm">{t.name}</p>
                <p className="text-slate-400 text-xs">{t.route} · {t.t}</p>
              </div>
              <p className="text-blue-700 font-bold text-sm flex-shrink-0">{t.fare}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};