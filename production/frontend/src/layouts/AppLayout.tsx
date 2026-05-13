import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Home, Map, Clock, User, BarChart2, MessageSquare,
  Bell, Car, ShieldCheck, Menu, X, Zap, ChevronLeft,
  ChevronRight, Navigation, Settings
} from 'lucide-react';

const mobileNavItems = [
  { path: '/', icon: Home, label: 'Home' },
  { path: '/booking', icon: Navigation, label: 'Book' },
  { path: '/tracking', icon: Map, label: 'Track' },
  { path: '/history', icon: Clock, label: 'History' },
  { path: '/chat', icon: MessageSquare, label: 'AI' },
];

const sidebarItems = [
  { path: '/', icon: Home, label: 'Passenger Home', section: 'Passenger' },
  { path: '/booking', icon: Navigation, label: 'Book a Ride', section: 'Passenger' },
  { path: '/tracking', icon: Map, label: 'Driver Tracking', section: 'Passenger' },
  { path: '/history', icon: Clock, label: 'Ride History', section: 'Passenger' },
  { path: '/driver', icon: Car, label: 'Driver Dashboard', section: 'Driver' },
  { path: '/analytics', icon: BarChart2, label: 'Analytics', section: 'Operations' },
  { path: '/chat', icon: MessageSquare, label: 'AI Assistant', section: 'Operations' },
  { path: '/admin', icon: ShieldCheck, label: 'Fleet Admin', section: 'Operations' },
  { path: '/notifications', icon: Bell, label: 'Notifications', section: 'Account' },
  { path: '/profile', icon: User, label: 'Profile', section: 'Account' },
];

export const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  const currentPage = sidebarItems.find(i => i.path === location.pathname);

  if (isMobile) {
    return (
      <div className="flex flex-col h-screen bg-slate-100 overflow-hidden">
        {/* Mobile Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-slate-200 shadow-sm z-20">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-blue-700 flex items-center justify-center shadow-brand">
              <Car size={15} className="text-white" />
            </div>
            <div>
              <span className="font-bold text-blue-900 text-base tracking-tight">RSI</span>
              <span className="text-blue-600 font-bold text-base">AI</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => navigate('/notifications')} className="relative p-2 text-slate-400 hover:text-blue-600 transition-colors rounded-xl hover:bg-slate-100">
              <Bell size={19} />
              <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white" />
            </button>
            <button onClick={() => navigate('/profile')} className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center text-white text-xs font-bold shadow-brand">
              M
            </button>
          </div>
        </div>

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
              className="h-full"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Mobile Bottom Navigation */}
        <div className="bg-white border-t border-slate-200 shadow-[0_-4px_20px_rgba(15,23,42,0.06)]">
          <div className="flex items-center justify-around py-2 px-2">
            {mobileNavItems.map((item) => {
              const active = location.pathname === item.path;
              return (
                <button
                  key={item.path}
                  onClick={() => navigate(item.path)}
                  className="flex flex-col items-center gap-1 px-2 py-2 rounded-xl transition-all"
                >
                  <div className={`p-1.5 rounded-xl transition-all ${active ? 'bg-blue-50' : ''}`}>
                    <item.icon size={20} className={active ? 'text-blue-600' : 'text-slate-400'} />
                  </div>
                  <span className={`text-[10px] font-semibold transition-colors ${active ? 'text-blue-600' : 'text-slate-400'}`}>
                    {item.label}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // Desktop Layout
  const sections = [...new Set(sidebarItems.map(i => i.section))];

  return (
    <div className="flex h-screen bg-slate-100 overflow-hidden">
      {/* Sidebar */}
      <motion.aside
        animate={{ width: sidebarOpen ? 252 : 72 }}
        transition={{ type: 'spring', stiffness: 320, damping: 32 }}
        className="flex-shrink-0 bg-blue-950 flex flex-col z-20 overflow-hidden shadow-[4px_0_24px_rgba(10,36,114,0.15)]"
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-blue-900/60">
          <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center flex-shrink-0 shadow-brand">
            <Car size={17} className="text-white" />
          </div>
          {sidebarOpen && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="overflow-hidden">
              <div className="flex items-baseline gap-0.5">
                <span className="font-bold text-lg text-white tracking-tight whitespace-nowrap">RSI</span>
                <span className="font-bold text-lg text-sky-400 whitespace-nowrap">AI</span>
              </div>
              <p className="text-blue-300/60 text-[10px] whitespace-nowrap">Mobility Platform</p>
            </motion.div>
          )}
        </div>

        {/* Nav Items */}
        <nav className="flex-1 py-4 px-2 overflow-y-auto space-y-4">
          {sections.map(section => {
            const items = sidebarItems.filter(i => i.section === section);
            return (
              <div key={section}>
                {sidebarOpen && (
                  <p className="text-blue-400/50 text-[10px] font-semibold uppercase tracking-widest px-3 mb-1">{section}</p>
                )}
                <div className="space-y-0.5">
                  {items.map((item) => {
                    const active = location.pathname === item.path;
                    return (
                      <button
                        key={item.path}
                        onClick={() => navigate(item.path)}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all group relative ${
                          active
                            ? 'bg-blue-600 text-white shadow-brand'
                            : 'text-blue-200/70 hover:bg-blue-900/60 hover:text-white'
                        }`}
                      >
                        <item.icon size={17} className="flex-shrink-0" />
                        {sidebarOpen && (
                          <span className="text-sm font-medium whitespace-nowrap">{item.label}</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </nav>

        {/* Collapse Button */}
        <div className="p-3 border-t border-blue-900/60">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center justify-center gap-2 p-2 rounded-xl text-blue-300/60 hover:text-white hover:bg-blue-900/60 transition-all"
          >
            {sidebarOpen ? <ChevronLeft size={15} /> : <ChevronRight size={15} />}
            {sidebarOpen && <span className="text-xs">Collapse</span>}
          </button>
        </div>
      </motion.aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Desktop Top Bar */}
        <header className="flex items-center justify-between px-6 py-3.5 bg-white border-b border-slate-200 shadow-sm">
          <div>
            <h1 className="text-slate-800 font-bold text-base">{currentPage?.label || 'Dashboard'}</h1>
            <p className="text-slate-400 text-xs">RSI AI Platform</p>
          </div>
          <div className="flex items-center gap-3">
            {/* WS Status */}
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 border border-emerald-100 rounded-lg">
              <span className="live-dot" />
              <span className="text-xs text-emerald-700 font-medium">Live</span>
            </div>
            <button onClick={() => navigate('/notifications')} className="relative p-2 text-slate-400 hover:text-blue-600 transition-colors rounded-xl hover:bg-slate-100">
              <Bell size={18} />
              <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white" />
            </button>
            <button onClick={() => navigate('/profile')} className="flex items-center gap-2.5 pl-2 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl hover:bg-slate-100 transition-all">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center text-white text-xs font-bold">M</div>
              <div className="text-left">
                <p className="text-slate-700 text-sm font-medium leading-none">Miftah</p>
                <p className="text-slate-400 text-[10px] mt-0.5">Gold Member</p>
              </div>
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto bg-slate-100">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.16, ease: 'easeOut' }}
              className="h-full"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
};
