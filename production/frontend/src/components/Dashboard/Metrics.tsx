import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

interface MetricsProps {
  data: Array<{ date: string; rides: number; revenue: number }>;
  loading?: boolean;
}

export const Metrics: React.FC<MetricsProps> = ({ data, loading }) => {
  if (loading) return <div>Loading metrics...</div>;
  
  return (
    <div className="metrics-container">
      <h2>Performance Metrics</h2>
      <BarChart width={600} height={300} data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="rides" fill="#8884d8" />
        <Bar dataKey="revenue" fill="#82ca9d" />
      </BarChart>
    </div>
  );
};