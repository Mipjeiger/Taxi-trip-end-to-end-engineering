import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { MapPin, Clock, Star, Navigation, ChevronRight, Shield, Zap, TrendingUp } from 'lucide-react';

const recentRides = [
  { id: 1, from: 'Sudirman Plaza', to: 'Senayan City', time: '2h ago', price: 'Rp 45.000', rating: 5, status: 'completed' },
  { id: 2, from: 'SCBD Tower', to: 'Gatot Subroto', time: 'Yesterday', price: 'Rp 28.000', rating: 4, status: 'completed' },
  { id: 3, from: 'Grand Indonesia', to: 'Kemang', time: '2 days ago', price: 'Rp 62.000', rating: 5, status: 'completed' },
];

const quickDest = [
  { label: 'Office', icon: '🏢', sub: 'SCBD, Jakarta Selatan' },
  { label: 'Home', icon: '🏠', sub: 'Kemang, Jakarta Selatan' },
  { label: 'Mall', icon: '🛍️', sub: 'Grand Indonesia' },
  { label: 'Airport', icon: '✈️', sub: 'Soekarno-Hatta Intl.' },
];

// Nearby drivers (animated dots on map)
const nearbyDrivers = [
  { top: '28%', left: '22%' }, { top: '48%', left: '58%' },
  { top: '35%', left: '70%' }, { top: '60%', left: '35%' },
];

export const Home: React.FC = () => {
  const navigate = useNavigate();
  const [greeting, setGreeting] = useState('');
  const [driverCount] = useState(14);

  useEffect(() => {
    const h = new Date().getHours();
    setGreeting(h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening');
  }, []);

  return (
    <div className="min-h-full bg-slate-100 pb-28 md:pb-8">

      {/* Map Hero */}
      <div className="relative h-60 md:h-72 bg-blue-950 overflow-hidden">
        {/* Grid lines simulating map */}
        <div className="absolute inset-0 opacity-30"
          style={{
            backgroundImage: `
              linear-gradient(rgba(96,165,250,0.15) 1px, transparent 1px),
              linear-gradient(90deg, rgba(96,165,250,0.15) 1px, transparent 1px)
            `,
            backgroundSize: '36px 36px',
          }}
        />
        {/* Road lines */}
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 400 240">
          <line x1="0" y1="120" x2="400" y2="120" stroke="rgba(148,163,184,0.15)" strokeWidth="8" />
          <line x1="200" y1="0" x2="200" y2="240" stroke="rgba(148,163,184,0.15)" strokeWidth="8" />
          <line x1="0" y1="60" x2="400" y2="60" stroke="rgba(148,163,184,0.07)" strokeWidth="4" />
          <line x1="0" y1="180" x2="400" y2="180" stroke="rgba(148,163,184,0.07)" strokeWidth="4" />
          <line x1="100" y1="0" x2="100" y2="240" stroke="rgba(148,163,184,0.07)" strokeWidth="4" />
          <line x1="300" y1="0" x2="300" y2="240" stroke="rgba(148,163,184,0.07)" strokeWidth="4" />
        </svg>

        {/* Animated driver dots */}
        {nearbyDrivers.map((pos, i) => (
          <div key={i} className="absolute" style={pos}>
            <div className="relative">
              <div className="absolute inset-0 w-5 h-5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-400/30 ring-pulse" />
              <div className="w-7 h-7 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white border-2 border-blue-500 shadow-lg flex items-center justify-center text-sm">🚗</div>
            </div>
          </div>
        ))}

        {/* You pin */}
        <div className="absolute" style={{ top: '50%', left: '50%', transform: 'translate(-50%,-50%)' }}>
          <div className="flex flex-col items-center pin-bounce">
            <div className="w-5 h-5 rounded-full bg-blue-600 border-2 border-white shadow-brand" />
            <div className="w-0.5 h-3 bg-blue-600" />
          </div>
        </div>

        {/* Gradient fade */}
        <div className="absolute bottom-0 inset-x-0 h-20 bg-gradient-to-t from-slate-100 to-transparent" />

        {/* Greeting overlay */}
        <div className="absolute top-5 left-4 md:left-8">
          <p className="text-blue-200 text-sm">{greeting} 👋</p>
          <h2 className="text-white font-bold text-2xl mt-0.5">Mip</h2>
        </div>

        {/* Drivers nearby pill */}
        <div className="absolute top-5 right-4 flex items-center gap-2 bg-white/10 backdrop-blur-md border border-white/20 px-3 py-1.5 rounded-full">
          <span className="live-dot" />
          <span className="text-white text-xs font-medium">{driverCount} drivers nearby</span>
        </div>
      </div>

      <div className="px-4 md:px-8 space-y-5 -mt-4">

        {/* Quick Book CTA */}
        <motion.button
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
          onClick={() => navigate('/booking')}
          className="w-full card p-4 flex items-center gap-4 hover:shadow-card-hover transition-all group border-l-4 border-blue-600"
        >
          <div className="w-11 h-11 rounded-xl bg-blue-600 flex items-center justify-center shadow-brand flex-shrink-0 group-hover:bg-blue-700 transition-colors">
            <Navigation size={20} className="text-white" />
          </div>
          <div className="flex-1 text-left">
            <p className="text-slate-400 text-xs">Where are you going?</p>
            <p className="text-slate-800 font-semibold mt-0.5">Book a ride in seconds</p>
          </div>
          <ChevronRight size={18} className="text-blue-500" />
        </motion.button>

        {/* Quick Destinations */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
          <p className="section-label mb-3">Quick destinations</p>
          <div className="grid grid-cols-2 gap-3">
            {quickDest.map((dest, i) => (
              <motion.button
                key={dest.label}
                initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.1 + i * 0.05 }}
                onClick={() => navigate('/booking')}
                className="card p-4 text-left hover:shadow-card-hover transition-all"
              >
                <span className="text-2xl">{dest.icon}</span>
                <p className="text-slate-800 font-semibold mt-2 text-sm">{dest.label}</p>
                <p className="text-slate-400 text-xs mt-0.5 truncate">{dest.sub}</p>
              </motion.button>
            ))}
          </div>
        </motion.div>

        {/* Stats Row */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} className="grid grid-cols-3 gap-3">
          {[
            { label: 'Total Rides', value: '142', icon: Navigation, color: 'text-blue-600', bg: 'bg-blue-50' },
            { label: 'Avg Rating', value: '4.92', icon: Star, color: 'text-amber-500', bg: 'bg-amber-50' },
            { label: 'Saved', value: 'Rp 12K', icon: TrendingUp, color: 'text-emerald-600', bg: 'bg-emerald-50' },
          ].map((s, i) => (
            <div key={s.label} className="card p-4 text-center">
              <div className={`w-8 h-8 rounded-xl ${s.bg} flex items-center justify-center mx-auto mb-2`}>
                <s.icon size={16} className={s.color} />
              </div>
              <p className="text-slate-800 font-bold text-lg">{s.value}</p>
              <p className="text-slate-400 text-xs">{s.label}</p>
            </div>
          ))}
        </motion.div>

        {/* Recent rides */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.25 }}>
          <div className="flex items-center justify-between mb-3">
            <p className="section-label">Recent rides</p>
            <button onClick={() => navigate('/history')} className="text-blue-600 text-xs font-semibold hover:underline">View all</button>
          </div>
          <div className="space-y-2">
            {recentRides.map((ride, i) => (
              <motion.div
                key={ride.id}
                initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.25 + i * 0.07 }}
                className="card p-4 flex items-center gap-4 hover:shadow-card-hover transition-all"
              >
                <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                  <MapPin size={16} className="text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <p className="text-slate-700 text-sm font-medium truncate">{ride.from}</p>
                    <ChevronRight size={11} className="text-slate-400 flex-shrink-0" />
                    <p className="text-slate-500 text-sm truncate">{ride.to}</p>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-slate-400 text-xs">{ride.time}</span>
                    <Star size={10} className="text-amber-400 fill-amber-400" />
                    <span className="text-slate-400 text-xs">{ride.rating}.0</span>
                  </div>
                </div>
                <p className="text-blue-700 font-semibold text-sm flex-shrink-0">{ride.price}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Safety Banner */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.35 }} className="card p-4 flex items-center gap-3 border-l-4 border-emerald-500">
          <div className="w-9 h-9 rounded-xl bg-emerald-50 flex items-center justify-center">
            <Shield size={16} className="text-emerald-600" />
          </div>
          <div>
            <p className="text-slate-700 text-sm font-semibold">AI Safety Monitoring Active</p>
            <p className="text-slate-400 text-xs">All routes monitored 24/7 in real-time</p>
          </div>
        </motion.div>
      </div>
    </div>
  );
};