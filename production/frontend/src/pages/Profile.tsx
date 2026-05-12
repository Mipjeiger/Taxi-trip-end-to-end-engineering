import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { User, CreditCard, Shield, Bell, ChevronRight, Edit3, Star, LogOut, ChevronDown } from 'lucide-react';

const payments = [
  { id: 'gopay', label: 'GoPay', balance: 'Rp 245.000', icon: '💚' },
  { id: 'ovo', label: 'OVO', balance: 'Rp 80.000', icon: '💜' },
  { id: 'visa', label: 'Visa ···· 4242', balance: '', icon: '💳' },
];

const settings = [
  { section: 'Account', items: [{ icon: User, label: 'Personal Information' }, { icon: Shield, label: 'Privacy & Safety' }, { icon: Bell, label: 'Notification Preferences' }] },
  { section: 'App', items: [{ icon: Star, label: 'Saved Places' }, { icon: CreditCard, label: 'Payment History' }] },
];

export const Profile: React.FC = () => {
  const [activePayment, setActive] = useState('gopay');

  return (
    <div className="page-container">
      <div className="max-w-lg mx-auto space-y-5">

        {/* User Card */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card p-6">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center text-3xl font-black text-white shadow-brand">M</div>
              <button className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center shadow-brand">
                <Edit3 size={10} className="text-white" />
              </button>
            </div>
            <div className="flex-1">
              <h2 className="text-slate-800 text-xl font-black">Miftah Hadiyan</h2>
              <p className="text-slate-400 text-sm">miftah@example.com</p>
              <div className="flex items-center gap-3 mt-2">
                <div className="flex items-center gap-1 text-amber-500 text-xs font-semibold"><Star size={11} fill="currentColor" />4.92</div>
                <span className="text-slate-200">·</span>
                <span className="text-slate-400 text-xs">142 rides</span>
              </div>
            </div>
          </div>

          {/* Loyalty Tier */}
          <div className="mt-4 bg-gradient-to-r from-amber-500/10 to-amber-400/5 border border-amber-200 rounded-xl px-4 py-3 flex items-center gap-3">
            <span className="text-xl">⭐</span>
            <div className="flex-1">
              <p className="text-amber-700 font-bold text-sm">GoRide Gold Member</p>
              <p className="text-amber-600/70 text-xs">2,400 pts · 600 to Platinum</p>
            </div>
            <div>
              <div className="h-1.5 w-24 bg-amber-100 rounded-full overflow-hidden">
                <div className="h-full w-3/4 bg-gradient-to-r from-amber-500 to-amber-400 rounded-full" />
              </div>
            </div>
          </div>
        </motion.div>

        {/* Payment Methods */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.08 }} className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-slate-700 font-bold">Payment Methods</h3>
            <button className="text-blue-600 text-xs font-semibold hover:underline">+ Add</button>
          </div>
          <div className="space-y-2">
            {payments.map(pm => (
              <button key={pm.id} onClick={() => setActive(pm.id)}
                className={`w-full flex items-center gap-3 p-3.5 rounded-xl border-2 transition-all ${activePayment === pm.id ? 'border-blue-500 bg-blue-50/50' : 'border-transparent bg-slate-50 hover:bg-slate-100'}`}>
                <span className="text-2xl">{pm.icon}</span>
                <div className="flex-1 text-left">
                  <p className="text-slate-700 text-sm font-semibold">{pm.label}</p>
                  {pm.balance && <p className="text-slate-400 text-xs">{pm.balance}</p>}
                </div>
                {activePayment === pm.id && <div className="w-5 h-5 rounded-full bg-blue-600 flex items-center justify-center"><span className="text-white text-[9px] font-bold">✓</span></div>}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Settings */}
        {settings.map((group, gi) => (
          <motion.div key={group.section} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.12 + gi * 0.05 }} className="card overflow-hidden">
            <p className="section-label px-5 pt-4 pb-2">{group.section}</p>
            {group.items.map((item, i) => (
              <button key={item.label} className={`w-full flex items-center gap-3 px-5 py-4 hover:bg-slate-50 transition-all ${i < group.items.length - 1 ? 'border-b border-slate-100' : ''}`}>
                <div className="w-8 h-8 rounded-xl bg-slate-100 flex items-center justify-center">
                  <item.icon size={15} className="text-slate-500" />
                </div>
                <span className="text-slate-600 text-sm flex-1 text-left">{item.label}</span>
                <ChevronRight size={14} className="text-slate-300" />
              </button>
            ))}
          </motion.div>
        ))}

        <button className="w-full card p-4 flex items-center justify-center gap-2 text-red-500 hover:bg-red-50 border-red-100 transition-all">
          <LogOut size={15} />
          <span className="text-sm font-semibold">Sign Out</span>
        </button>
      </div>
    </div>
  );
};
