import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Bell, Car, DollarSign, Shield, CheckCheck } from 'lucide-react';

type Notif = { id: number; Icon: React.ComponentType<any>; iconBg: string; iconColor: string; title: string; desc: string; time: string; read: boolean; type: string };

const initial: Notif[] = [
  { id: 1, Icon: Car, iconBg: 'bg-blue-50', iconColor: 'text-blue-600', title: 'Driver is 2 mins away', desc: 'Ahmad R. is approaching in Honda Beat B 1234 XY', time: 'Just now', read: false, type: 'ride' },
  { id: 2, Icon: Bell, iconBg: 'bg-blue-50', iconColor: 'text-blue-600', title: 'AI Route Optimized', desc: 'Your route was updated due to Sudirman jam. Saving 10 minutes!', time: '5 min ago', read: false, type: 'ride' },
  { id: 3, Icon: DollarSign, iconBg: 'bg-emerald-50', iconColor: 'text-emerald-600', title: 'Payment Confirmed', desc: 'Rp 45,000 charged via GoPay for your last ride', time: '2h ago', read: false, type: 'payment' },
  { id: 4, Icon: Bell, iconBg: 'bg-amber-50', iconColor: 'text-amber-600', title: '25% Off – This Weekend!', desc: 'Use code WEEKEND25 for 25% off all GoRide AI trips. Valid till Sunday.', time: '1 day ago', read: true, type: 'promo' },
  { id: 5, Icon: Shield, iconBg: 'bg-blue-50', iconColor: 'text-blue-600', title: 'Safety Check Complete', desc: 'Your trip was confirmed safe by AI monitoring.', time: '2 days ago', read: true, type: 'safety' },
  { id: 6, Icon: Car, iconBg: 'bg-blue-50', iconColor: 'text-blue-600', title: 'Ride Completed', desc: 'SCBD → Kemang · Rp 62,000 · Please rate your driver', time: '3 days ago', read: true, type: 'ride' },
];

export const Notifications: React.FC = () => {
  const [notifs, setNotifs] = useState(initial);
  const [filter, setFilter] = useState('all');
  const unread = notifs.filter(n => !n.read).length;

  const markAll = () => setNotifs(p => p.map(n => ({ ...n, read: true })));
  const markOne = (id: number) => setNotifs(p => p.map(n => n.id === id ? { ...n, read: true } : n));

  const filtered = notifs.filter(n => filter === 'all' || n.type === filter);

  return (
    <div className="page-container">
      <div className="max-w-lg mx-auto space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-slate-800 font-black text-2xl">Notifications</h1>
            {unread > 0 && <p className="text-blue-600 text-sm font-semibold mt-0.5">{unread} unread</p>}
          </div>
          {unread > 0 && (
            <button onClick={markAll} className="flex items-center gap-1.5 text-slate-500 hover:text-blue-600 transition-colors text-xs font-semibold">
              <CheckCheck size={14} />Mark all read
            </button>
          )}
        </div>

        {/* Filter tabs */}
        <div className="flex gap-2 flex-wrap">
          {['all', 'ride', 'promo', 'payment', 'safety'].map(f => (
            <button key={f} onClick={() => setFilter(f)} className={`px-4 py-1.5 rounded-full text-sm font-semibold capitalize transition-all ${filter === f ? 'bg-blue-700 text-white shadow-brand' : 'bg-white border border-slate-200 text-slate-500 hover:bg-slate-50'}`}>
              {f}
            </button>
          ))}
        </div>

        {/* List */}
        <div className="space-y-2">
          {filtered.map((n, i) => (
            <motion.div key={n.id} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
              onClick={() => markOne(n.id)}
              className={`card p-4 flex items-start gap-4 cursor-pointer hover:shadow-card-hover transition-all ${!n.read ? 'border-l-4 border-blue-500' : ''}`}>
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5 ${n.iconBg}`}>
                <n.Icon size={16} className={n.iconColor} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className={`text-sm font-semibold ${!n.read ? 'text-slate-800' : 'text-slate-600'}`}>{n.title}</p>
                  {!n.read && <div className="w-2 h-2 rounded-full bg-blue-600 flex-shrink-0" />}
                </div>
                <p className="text-slate-400 text-xs mt-0.5 leading-relaxed">{n.desc}</p>
              </div>
              <span className="text-slate-400 text-xs flex-shrink-0 whitespace-nowrap">{n.time}</span>
            </motion.div>
          ))}
        </div>

        {filtered.length === 0 && (
          <div className="text-center py-16">
            <Bell size={36} className="text-slate-300 mx-auto mb-4" />
            <p className="text-slate-500 font-semibold">No notifications</p>
          </div>
        )}
      </div>
    </div>
  );
};
