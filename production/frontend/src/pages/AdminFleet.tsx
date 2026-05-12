import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Car, Users, Activity, Zap, AlertTriangle, MapPin, RefreshCw } from 'lucide-react';

type Status = 'in_trip' | 'active' | 'idle' | 'offline';

type Driver = { id: number; name: string; status: Status; location: string; trips: number; earning: string; rating: number };

const DRIVERS: Driver[] = [
  { id: 1, name: 'Ahmad Rizki', status: 'in_trip', location: 'Sudirman → Kemang', trips: 12, earning: 'Rp 480K', rating: 4.9 },
  { id: 2, name: 'Budi Santoso', status: 'active', location: 'SCBD, Jakarta', trips: 8, earning: 'Rp 320K', rating: 4.7 },
  { id: 3, name: 'Citra Dewi', status: 'idle', location: 'Kuningan, Jakarta', trips: 5, earning: 'Rp 200K', rating: 4.8 },
  { id: 4, name: 'Dian Pratama', status: 'in_trip', location: 'Semanggi → Blok M', trips: 10, earning: 'Rp 400K', rating: 4.6 },
  { id: 5, name: 'Eka Fauzi', status: 'offline', location: 'Last seen: Menteng', trips: 3, earning: 'Rp 120K', rating: 4.5 },
  { id: 6, name: 'Fajar Nugroho', status: 'active', location: 'Thamrin, Jakarta', trips: 9, earning: 'Rp 360K', rating: 4.9 },
  { id: 7, name: 'Gina Rahayu', status: 'in_trip', location: 'Senen → Cikini', trips: 7, earning: 'Rp 280K', rating: 4.7 },
  { id: 8, name: 'Hendra Liu', status: 'active', location: 'PIK, Jakarta Utara', trips: 6, earning: 'Rp 240K', rating: 4.8 },
];

const SC: Record<Status, { label: string; class: string }> = {
  in_trip: { label: 'In Trip', class: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  active: { label: 'Online', class: 'bg-blue-50 text-blue-700 border-blue-200' },
  idle: { label: 'Idle', class: 'bg-amber-50 text-amber-700 border-amber-200' },
  offline: { label: 'Offline', class: 'bg-slate-100 text-slate-500 border-slate-200' },
};

export const AdminFleet: React.FC = () => {
  const [filter, setFilter] = useState<'all' | Status>('all');
  const [updated, setUpdated] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setUpdated(new Date()), 5000);
    return () => clearInterval(id);
  }, []);

  const counts = { in_trip: DRIVERS.filter(d => d.status === 'in_trip').length, active: DRIVERS.filter(d => d.status === 'active').length, idle: DRIVERS.filter(d => d.status === 'idle').length, offline: DRIVERS.filter(d => d.status === 'offline').length };
  const filtered = DRIVERS.filter(d => filter === 'all' || d.status === filter);

  return (
    <div className="page-container space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-slate-800 font-black text-2xl">Fleet Monitor</h1>
          <div className="flex items-center gap-1.5 mt-0.5"><span className="live-dot" /><p className="text-slate-400 text-xs">Updated {updated.toLocaleTimeString()}</p></div>
        </div>
        <button className="btn-ghost border border-slate-200 flex items-center gap-1.5 text-sm"><RefreshCw size={13} />Refresh</button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'In Trip', count: counts.in_trip, icon: Car, bg: 'bg-emerald-50', ic: 'text-emerald-600', s: 'in_trip' as Status },
          { label: 'Online', count: counts.active, icon: Activity, bg: 'bg-blue-50', ic: 'text-blue-600', s: 'active' as Status },
          { label: 'Idle', count: counts.idle, icon: Zap, bg: 'bg-amber-50', ic: 'text-amber-500', s: 'idle' as Status },
          { label: 'Offline', count: counts.offline, icon: Users, bg: 'bg-slate-100', ic: 'text-slate-500', s: 'offline' as Status },
        ].map((k, i) => (
          <motion.button key={k.label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}
            onClick={() => setFilter(filter === k.s ? 'all' : k.s)}
            className={`card p-4 text-left hover:shadow-card-hover transition-all ${filter === k.s ? 'ring-2 ring-blue-500 ring-offset-2' : ''}`}>
            <div className={`w-9 h-9 rounded-xl ${k.bg} flex items-center justify-center mb-3`}>
              <k.icon size={16} className={k.ic} />
            </div>
            <p className="text-slate-800 font-black text-2xl">{k.count}</p>
            <p className="text-slate-400 text-sm">{k.label}</p>
          </motion.button>
        ))}
      </div>

      {/* AI Fleet Alerts */}
      <div className="card p-4 border-l-4 border-amber-400">
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle size={15} className="text-amber-500" />
          <span className="text-amber-700 font-bold text-sm">Fleet Alerts</span>
          <span className="ml-auto badge-amber"><span className="live-dot" style={{ background: '#F59E0B' }} />3 active</span>
        </div>
        <div className="space-y-2">
          {[
            '⚠️ Kemang zone underserved — only 2 drivers active. Recommend deploying 5 more.',
            '📍 Citra Dewi idle 45 min in low-demand area. Recommend relocation to SCBD.',
            '🚦 Heavy traffic on Thamrin. ETA delays +8 min for active in-trip drivers.',
          ].map((a, i) => <p key={i} className="text-slate-600 text-xs leading-relaxed">{a}</p>)}
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        {(['all', 'in_trip', 'active', 'idle', 'offline'] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)} className={`px-4 py-1.5 rounded-full text-sm font-semibold capitalize transition-all ${filter === f ? 'bg-blue-700 text-white shadow-brand' : 'bg-white border border-slate-200 text-slate-500 hover:bg-slate-50'}`}>
            {f === 'in_trip' ? 'In Trip' : f === 'all' ? 'All Drivers' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Driver Table */}
      <div className="card overflow-hidden">
        <div className="hidden md:grid grid-cols-5 gap-4 px-5 py-3 border-b border-slate-100 bg-slate-50">
          {['Driver', 'Status', 'Location', 'Trips', 'Today\'s Earnings'].map(h => (
            <span key={h} className="section-label">{h}</span>
          ))}
        </div>
        {filtered.map((d, i) => (
          <motion.div key={d.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.04 }}
            className={`flex flex-col md:grid md:grid-cols-5 gap-3 md:gap-4 px-5 py-4 hover:bg-slate-50 transition-all ${i < filtered.length - 1 ? 'border-b border-slate-100' : ''}`}>
            {/* Name */}
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-blue-50 flex items-center justify-center text-base flex-shrink-0">👤</div>
              <div>
                <p className="text-slate-700 font-semibold text-sm">{d.name}</p>
                <p className="text-slate-400 text-xs">⭐ {d.rating}</p>
              </div>
            </div>
            {/* Status */}
            <div className="md:flex md:items-center">
              <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${SC[d.status].class}`}>{SC[d.status].label}</span>
            </div>
            {/* Location */}
            <div className="flex items-center gap-1.5 text-slate-400 text-xs">
              <MapPin size={11} className="flex-shrink-0" />
              <span className="truncate">{d.location}</span>
            </div>
            {/* Trips */}
            <div className="md:flex md:items-center text-slate-600 text-sm font-semibold">{d.trips} trips</div>
            {/* Earning */}
            <div className="md:flex md:items-center text-blue-700 text-sm font-bold">{d.earning}</div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};
