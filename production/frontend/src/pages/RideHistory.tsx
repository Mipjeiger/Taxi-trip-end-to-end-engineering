import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { MapPin, Star, Search, Download, ChevronRight, Clock } from 'lucide-react';

const rides = [
  { id: 1, from: 'Sudirman Plaza', to: 'Senayan City', date: 'Today, 08:12', price: 'Rp 45.000', rating: 5, type: 'GoRide AI', status: 'completed' },
  { id: 2, from: 'SCBD Tower', to: 'Gatot Subroto', date: 'Yesterday, 17:45', price: 'Rp 28.000', rating: 4, type: 'GoX Economy', status: 'completed' },
  { id: 3, from: 'Grand Indonesia', to: 'Kemang', date: 'May 10, 20:30', price: 'Rp 62.000', rating: 5, type: 'GoCar', status: 'completed' },
  { id: 4, from: 'Kuningan City', to: 'Blok M', date: 'May 9, 09:00', price: 'Rp 41.000', rating: 4, type: 'GoRide AI', status: 'completed' },
  { id: 5, from: 'Menteng', to: 'PIK', date: 'May 8, 18:20', price: 'Rp 89.000', rating: 5, type: 'GoSUV', status: 'completed' },
  { id: 6, from: 'Cikini', to: 'Kota Tua', date: 'May 7, 11:00', price: 'Rp 33.000', rating: 3, type: 'GoX Economy', status: 'cancelled' },
];

export const RideHistory: React.FC = () => {
  const [filter, setFilter] = useState<'all' | 'completed' | 'cancelled'>('all');
  const [search, setSearch] = useState('');

  const filtered = rides.filter(r => {
    if (filter !== 'all' && r.status !== filter) return false;
    if (search && ![r.from, r.to].some(t => t.toLowerCase().includes(search.toLowerCase()))) return false;
    return true;
  });

  const totalSpent = rides.filter(r => r.status === 'completed').reduce((a, r) => a + parseInt(r.price.replace(/\D/g, '')), 0);

  return (
    <div className="page-container">
      <div className="max-w-2xl mx-auto space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-slate-800 font-black text-2xl">Ride History</h1>
            <p className="text-slate-400 text-sm">{rides.length} total rides</p>
          </div>
          <button className="w-10 h-10 rounded-xl bg-white border border-slate-200 flex items-center justify-center text-slate-500 hover:bg-slate-50 transition-all shadow-card">
            <Download size={16} />
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Total Spent', value: `Rp ${(totalSpent / 1000).toFixed(0)}K` },
            { label: 'Completed', value: String(rides.filter(r => r.status === 'completed').length) },
            { label: 'Avg Rating', value: (rides.reduce((a, r) => a + r.rating, 0) / rides.length).toFixed(1) },
          ].map((s, i) => (
            <motion.div key={s.label} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }} className="card p-4 text-center">
              <p className="text-blue-700 font-black text-lg">{s.value}</p>
              <p className="text-slate-400 text-xs mt-0.5">{s.label}</p>
            </motion.div>
          ))}
        </div>

        {/* Search */}
        <div className="relative">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search rides..." className="input-base pl-9" />
        </div>

        {/* Filter tabs */}
        <div className="flex gap-2">
          {(['all', 'completed', 'cancelled'] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)} className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-all ${filter === f ? 'bg-blue-700 text-white shadow-brand' : 'bg-white border border-slate-200 text-slate-500 hover:bg-slate-50'}`}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        {/* List */}
        <div className="space-y-2.5">
          {filtered.map((ride, i) => (
            <motion.div key={ride.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
              className="card p-4 hover:shadow-card-hover transition-all cursor-pointer">
              <div className="flex items-start gap-4">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5 ${ride.status === 'cancelled' ? 'bg-red-50' : 'bg-blue-50'}`}>
                  <MapPin size={16} className={ride.status === 'cancelled' ? 'text-red-500' : 'text-blue-600'} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <p className="text-slate-700 text-sm font-semibold truncate">{ride.from}</p>
                    <ChevronRight size={11} className="text-slate-400 flex-shrink-0" />
                    <p className="text-slate-500 text-sm truncate">{ride.to}</p>
                  </div>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    <span className="text-slate-400 text-xs">{ride.date}</span>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${ride.status === 'completed' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'}`}>
                      {ride.status}
                    </span>
                    <span className="text-slate-400 text-xs">{ride.type}</span>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className={`font-bold text-sm ${ride.status === 'cancelled' ? 'text-slate-400 line-through' : 'text-blue-700'}`}>{ride.price}</p>
                  {ride.status === 'completed' && (
                    <div className="flex items-center justify-end gap-0.5 mt-1">
                      {Array.from({ length: 5 }).map((_, si) => (
                        <Star key={si} size={9} className={si < ride.rating ? 'text-amber-400 fill-amber-400' : 'text-slate-200 fill-slate-200'} />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {filtered.length === 0 && (
          <div className="text-center py-16">
            <Clock size={40} className="text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500 font-semibold">No rides found</p>
            <p className="text-slate-400 text-sm mt-1">Try adjusting your filters</p>
          </div>
        )}
      </div>
    </div>
  );
};
