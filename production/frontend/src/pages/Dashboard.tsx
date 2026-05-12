import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';
import { TrendingUp, TrendingDown, Users, Zap, DollarSign, Activity, MapPin, BarChart2 } from 'lucide-react';

const hourlyData = [
  { t: '00', rides: 10, rev: 350 }, { t: '04', rides: 4, rev: 140 }, { t: '08', rides: 52, rev: 1820 },
  { t: '12', rides: 38, rev: 1330 }, { t: '16', rides: 65, rev: 2275 }, { t: '20', rides: 58, rev: 2030 }, { t: '23', rides: 20, rev: 700 },
];
const weekData = [
  { d: 'Mon', rides: 320, drivers: 45 }, { d: 'Tue', rides: 390, drivers: 52 }, { d: 'Wed', rides: 280, drivers: 38 },
  { d: 'Thu', rides: 450, drivers: 60 }, { d: 'Fri', rides: 520, drivers: 68 }, { d: 'Sat', rides: 480, drivers: 62 }, { d: 'Sun', rides: 220, drivers: 35 },
];
const pieData = [
  { name: 'GoX Economy', value: 38 }, { name: 'GoRide AI', value: 30 },
  { name: 'GoCar', value: 22 }, { name: 'GoSUV', value: 10 },
];
const PIE_COLORS = ['#1D6FE8', '#0EA5E9', '#60A5FA', '#93C5FD'];
const hotZones = [
  { area: 'SCBD / Sudirman', rides: 1840, pct: 92 },
  { area: 'Kemang / Bangka', rides: 1240, pct: 62 },
  { area: 'Grand Indonesia', rides: 1080, pct: 54 },
  { area: 'Soetta Airport', rides: 980, pct: 49 },
  { area: 'Kuningan', rides: 860, pct: 43 },
];

const Tip = ({ active, payload, label }: any) => active && payload?.length ? (
  <div className="card px-3 py-2 border-blue-100">
    <p className="text-slate-400 text-xs">{label}</p>
    <p className="text-blue-700 font-bold text-sm">{payload[0]?.value?.toLocaleString()}</p>
  </div>
) : null;

export const Dashboard: React.FC = () => {
  const [liveDrivers, setLiveDrivers] = useState(143);
  useEffect(() => {
    const id = setInterval(() => setLiveDrivers(p => p + Math.floor(Math.random() * 5) - 2), 3000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="page-container space-y-5">
      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Rides Today', value: '1,842', change: '+12%', up: true, icon: Zap, bg: 'bg-blue-50', ic: 'text-blue-600' },
          { label: 'Active Drivers', value: String(liveDrivers), change: 'Live', live: true, icon: Users, bg: 'bg-sky-50', ic: 'text-sky-500' },
          { label: "Today's Revenue", value: 'Rp 8.4M', change: '+8%', up: true, icon: DollarSign, bg: 'bg-emerald-50', ic: 'text-emerald-600' },
          { label: 'Avg Rating', value: '4.87', change: '+0.02', up: true, icon: Activity, bg: 'bg-amber-50', ic: 'text-amber-500' },
        ].map((kpi, i) => (
          <motion.div key={kpi.label} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }} className="card p-5">
            <div className="flex items-start justify-between mb-4">
              <div className={`w-9 h-9 rounded-xl ${kpi.bg} flex items-center justify-center`}>
                <kpi.icon size={16} className={kpi.ic} />
              </div>
              <span className={`text-xs font-semibold flex items-center gap-1 ${kpi.live ? 'text-emerald-600' : kpi.up ? 'text-emerald-600' : 'text-red-500'}`}>
                {kpi.live ? <><span className="live-dot" />{kpi.change}</> : kpi.change}
              </span>
            </div>
            <p className="text-slate-800 font-black text-2xl">{kpi.value}</p>
            <p className="text-slate-400 text-xs mt-1">{kpi.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Charts Row 1 */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-slate-700 font-bold">Hourly Rides</h3>
            <span className="badge-blue">Today</span>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={hourlyData}>
              <defs>
                <linearGradient id="rideFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="t" tick={{ fill: '#94A3B8', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip content={<Tip />} />
              <Area type="monotone" dataKey="rides" stroke="#3B82F6" strokeWidth={2.5} fill="url(#rideFill)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-slate-700 font-bold">Weekly Overview</h3>
            <span className="badge-blue">This week</span>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={weekData} barGap={3}>
              <XAxis dataKey="d" tick={{ fill: '#94A3B8', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip content={<Tip />} />
              <Bar dataKey="rides" fill="#1D6FE8" radius={[4, 4, 0, 0]} />
              <Bar dataKey="drivers" fill="#93C5FD" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid md:grid-cols-3 gap-4">
        {/* Revenue line */}
        <div className="md:col-span-2 card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-slate-700 font-bold">Revenue Trend</h3>
            <span className="badge-green flex items-center gap-1"><TrendingUp size={10} />+8% vs yesterday</span>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={hourlyData}>
              <XAxis dataKey="t" tick={{ fill: '#94A3B8', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip content={<Tip />} />
              <Line type="monotone" dataKey="rev" stroke="#1D6FE8" strokeWidth={2.5} dot={{ fill: '#1D6FE8', r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Pie chart */}
        <div className="card p-5 flex flex-col">
          <h3 className="text-slate-700 font-bold mb-4">Ride Type Mix</h3>
          <div className="flex-1 flex flex-col items-center justify-center">
            <PieChart width={140} height={140}>
              <Pie data={pieData} cx={70} cy={70} innerRadius={40} outerRadius={65} dataKey="value" strokeWidth={0}>
                {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
              </Pie>
            </PieChart>
            <div className="mt-3 space-y-1.5 w-full">
              {pieData.map((d, i) => (
                <div key={d.name} className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: PIE_COLORS[i] }} />
                  <span className="text-slate-500 text-xs flex-1 truncate">{d.name}</span>
                  <span className="text-slate-700 text-xs font-semibold">{d.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Hot Zones + AI Insights */}
      <div className="grid md:grid-cols-2 gap-4">
        {/* Hot zones */}
        <div className="card p-5">
          <h3 className="text-slate-700 font-bold mb-4">Hot Zones</h3>
          <div className="space-y-3.5">
            {hotZones.map((z, i) => (
              <div key={z.area}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-slate-600 text-xs">{z.area}</span>
                  <span className="text-blue-700 text-xs font-bold">{z.rides.toLocaleString()} rides</span>
                </div>
                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div initial={{ width: 0 }} animate={{ width: `${z.pct}%` }} transition={{ delay: i * 0.1, duration: 0.6 }}
                    className="h-full bg-gradient-to-r from-blue-600 to-sky-400 rounded-full" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* AI Insights Panel */}
        <div className="card p-5 border-l-4 border-blue-600">
          <div className="flex items-center gap-2 mb-4">
            <Zap size={15} className="text-blue-600" />
            <h3 className="text-slate-700 font-bold">AI Operational Insights</h3>
            <div className="ml-auto flex items-center gap-1.5 badge-blue"><span className="live-dot" />Live</div>
          </div>
          <div className="space-y-3">
            {[
              { icon: '🚦', title: 'Traffic Alert', desc: 'Heavy congestion on Sudirman. 23 drivers auto-rerouted via HR Rasuna Said.', border: 'border-amber-200 bg-amber-50' },
              { icon: '📈', title: 'Demand Surge', desc: 'Kemang zone at 4.2x demand. Deploy 15 more drivers immediately.', border: 'border-blue-200 bg-blue-50' },
              { icon: '⚡', title: 'Peak Incoming', desc: 'Friday evening peak in 45 min. Incentive bonuses triggered for 30 drivers.', border: 'border-emerald-200 bg-emerald-50' },
            ].map((ins, i) => (
              <div key={i} className={`p-3 rounded-xl border ${ins.border}`}>
                <p className="text-slate-700 text-sm font-semibold">{ins.icon} {ins.title}</p>
                <p className="text-slate-500 text-xs mt-0.5 leading-relaxed">{ins.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};