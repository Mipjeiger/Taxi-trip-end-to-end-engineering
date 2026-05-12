import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { MapPin, Navigation, Clock, ChevronRight, Car, Zap, Shield, Search } from 'lucide-react';

const rideOptions = [
  { id: 'go-x', label: 'GoX Economy', icon: '🛺', eta: '3 min', price: 'Rp 28.000', priceVal: 28000, desc: 'Affordable everyday ride' },
  { id: 'go-ride', label: 'GoRide AI', icon: '⚡', eta: '2 min', price: 'Rp 35.000', priceVal: 35000, desc: 'AI-optimized fast route' },
  { id: 'go-car', label: 'GoCar', icon: '🚗', eta: '4 min', price: 'Rp 52.000', priceVal: 52000, desc: 'Comfortable 4-seater' },
  { id: 'go-suv', label: 'GoSUV Premium', icon: '🚙', eta: '6 min', price: 'Rp 78.000', priceVal: 78000, desc: 'Premium 6-seater SUV' },
];

const suggestions = [
  { label: 'SCBD Tower, Jakarta Selatan', icon: '🏢' },
  { label: 'Grand Indonesia, Thamrin', icon: '🛍️' },
  { label: 'Soekarno-Hatta Airport', icon: '✈️' },
];

export const RideBooking: React.FC = () => {
  const navigate = useNavigate();
  const [pickup, setPickup] = useState('');
  const [destination, setDestination] = useState('');
  const [selected, setSelected] = useState('go-ride');
  const [step, setStep] = useState<'input' | 'select' | 'confirming' | 'booked'>('input');
  const [loading, setLoading] = useState(false);

  const chosen = rideOptions.find(r => r.id === selected)!;

  const handleSearch = () => { if (pickup && destination) setStep('select'); };
  const handleBook = () => {
    setLoading(true);
    setStep('confirming');
    setTimeout(() => { setLoading(false); setStep('booked'); }, 2000);
  };

  return (
    <div className="min-h-full bg-slate-100 pb-28 md:pb-8">
      {/* Map Background */}
      <div className="relative h-56 md:h-72 bg-blue-950 overflow-hidden">
        <div className="absolute inset-0" style={{
          backgroundImage: `linear-gradient(rgba(96,165,250,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(96,165,250,0.08) 1px, transparent 1px)`,
          backgroundSize: '32px 32px',
        }} />
        {/* Road SVG */}
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 400 220">
          <line x1="0" y1="110" x2="400" y2="110" stroke="rgba(148,163,184,0.12)" strokeWidth="10" />
          <line x1="200" y1="0" x2="200" y2="220" stroke="rgba(148,163,184,0.12)" strokeWidth="10" />
          {step !== 'input' && (
            <motion.path d="M 70 170 Q 140 80 330 65" stroke="#3B82F6" strokeWidth="3" fill="none"
              strokeDasharray="10 5" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1 }} />
          )}
          {step !== 'input' && <>
            <motion.circle cx="70" cy="170" r="7" fill="#3B82F6" initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.2 }} />
            <motion.circle cx="330" cy="65" r="7" fill="#1652C7" initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 1 }} />
          </>}
        </svg>
        {step !== 'input' && (
          <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.5 }}
            className="absolute" style={{ top: '30%', left: '50%' }}>
            <div className="w-9 h-9 rounded-full bg-white border-2 border-blue-500 shadow-brand flex items-center justify-center text-lg">🚗</div>
          </motion.div>
        )}
        <div className="absolute bottom-0 inset-x-0 h-16 bg-gradient-to-t from-slate-100 to-transparent" />

        {step === 'input' && (
          <div className="absolute top-5 inset-x-4 md:inset-x-8">
            <h2 className="text-white font-bold text-xl">Where to?</h2>
            <p className="text-blue-300 text-sm mt-0.5">Enter your pickup and destination</p>
          </div>
        )}
      </div>

      <div className="px-4 md:px-8 -mt-4 space-y-4">
        <AnimatePresence mode="wait">

          {/* Step 1: Input */}
          {step === 'input' && (
            <motion.div key="input" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <div className="card p-5 space-y-3">
                {/* Pickup */}
                <div className="relative">
                  <div className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-blue-600 border-2 border-white shadow" />
                  <input value={pickup} onChange={e => setPickup(e.target.value)} placeholder="Pickup location" className="input-base pl-9" />
                </div>
                {/* Dashed connector */}
                <div className="flex items-center gap-2 pl-3.5">
                  <div className="flex flex-col gap-0.5">
                    {[0,1,2].map(i => <div key={i} className="w-0.5 h-1 bg-slate-300 rounded" />)}
                  </div>
                </div>
                {/* Destination */}
                <div className="relative">
                  <MapPin size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-blue-700" />
                  <input value={destination} onChange={e => setDestination(e.target.value)} placeholder="Where are you going?" className="input-base pl-9" />
                </div>
                <button onClick={handleSearch} disabled={!pickup || !destination} className="btn-brand w-full h-12 text-base disabled:opacity-50">
                  Find Rides
                </button>
              </div>

              {/* Suggestions */}
              <div className="mt-3">
                <p className="section-label mb-2">Recent & saved</p>
                {suggestions.map((s, i) => (
                  <button key={i} onClick={() => { setDestination(s.label); setPickup('Current Location'); }}
                    className="w-full flex items-center gap-3 card p-3.5 mb-2 text-left hover:shadow-card-hover transition-all">
                    <span className="text-xl">{s.icon}</span>
                    <span className="text-slate-600 text-sm">{s.label}</span>
                  </button>
                ))}
              </div>
            </motion.div>
          )}

          {/* Step 2: Select */}
          {step === 'select' && (
            <motion.div key="select" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-3">
              {/* Route bar */}
              <div className="card p-3 flex items-center gap-2 text-sm">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500 flex-shrink-0" />
                <span className="text-slate-600 truncate flex-1">{pickup}</span>
                <ChevronRight size={13} className="text-slate-400 flex-shrink-0" />
                <span className="text-slate-600 truncate flex-1">{destination}</span>
                <button onClick={() => setStep('input')} className="text-blue-600 text-xs font-semibold ml-2 flex-shrink-0">Edit</button>
              </div>

              <h3 className="text-slate-700 font-bold">Choose your ride</h3>
              {rideOptions.map(opt => (
                <motion.button key={opt.id} onClick={() => setSelected(opt.id)} whileTap={{ scale: 0.99 }}
                  className={`w-full card p-4 flex items-center gap-4 transition-all border-2 ${selected === opt.id ? 'border-blue-500 bg-blue-50/50' : 'border-transparent hover:border-slate-200'}`}>
                  <span className="text-3xl">{opt.icon}</span>
                  <div className="flex-1 text-left">
                    <p className="text-slate-800 font-semibold text-sm">{opt.label}</p>
                    <p className="text-slate-400 text-xs">{opt.desc} · {opt.eta}</p>
                  </div>
                  <div className="text-right">
                    <p className={`font-bold text-sm ${selected === opt.id ? 'text-blue-600' : 'text-slate-700'}`}>{opt.price}</p>
                  </div>
                  {selected === opt.id && <div className="w-5 h-5 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0"><span className="text-white text-[9px] font-bold">✓</span></div>}
                </motion.button>
              ))}

              {/* AI insight */}
              <div className="card p-4 border-l-4 border-blue-500">
                <div className="flex items-center gap-2 mb-1">
                  <Zap size={13} className="text-blue-600" />
                  <span className="text-blue-700 font-semibold text-xs">AI Route Insight</span>
                </div>
                <p className="text-slate-500 text-xs">GoRide AI routes via HR Rasuna Said today — avoids Sudirman traffic, saving ~8 min.</p>
              </div>

              <button onClick={handleBook} className="btn-brand w-full h-14 text-base">
                Confirm {chosen.label} · {chosen.price}
              </button>
            </motion.div>
          )}

          {/* Step 3: Confirming */}
          {step === 'confirming' && (
            <motion.div key="confirming" initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col items-center py-16 gap-6">
              <div className="relative w-20 h-20">
                <div className="absolute inset-0 rounded-full border-4 border-blue-100 border-t-blue-600 animate-spin" />
                <div className="absolute inset-4 rounded-full bg-blue-50 flex items-center justify-center">
                  <Car size={22} className="text-blue-600" />
                </div>
              </div>
              <div className="text-center">
                <p className="text-slate-800 font-bold text-xl">Matching your driver...</p>
                <p className="text-slate-400 text-sm mt-1">AI is finding the best driver nearby</p>
              </div>
              <div className="flex gap-1.5">
                {[0,1,2].map(i => <div key={i} className="w-2 h-2 rounded-full bg-blue-300 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />)}
              </div>
            </motion.div>
          )}

          {/* Step 4: Booked */}
          {step === 'booked' && (
            <motion.div key="booked" initial={{ opacity: 0, scale: 0.92 }} animate={{ opacity: 1, scale: 1 }} className="space-y-3">
              <div className="card p-6 text-center">
                <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 380 }}
                  className="w-16 h-16 rounded-2xl bg-emerald-50 border-2 border-emerald-300 flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">✓</span>
                </motion.div>
                <h3 className="text-slate-800 font-bold text-xl">Driver Found!</h3>
                <p className="text-slate-400 text-sm mt-1">Ahmad R. is on his way to you</p>
              </div>
              <div className="card p-4 flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center text-2xl">👨</div>
                <div className="flex-1">
                  <p className="text-slate-800 font-bold">Ahmad Rizki</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-amber-500 text-xs font-semibold">★ 4.9</span>
                    <span className="text-slate-300">·</span>
                    <span className="text-slate-500 text-xs">Honda Beat · B 1234 XY</span>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-blue-600 font-bold text-lg">{chosen.eta}</p>
                  <p className="text-slate-400 text-xs">away</p>
                </div>
              </div>
              <button onClick={() => navigate('/tracking')} className="btn-brand w-full h-12">
                Track Driver Live →
              </button>
              <button onClick={() => navigate('/')} className="btn-ghost w-full h-12 text-sm border border-slate-200">Back to Home</button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};