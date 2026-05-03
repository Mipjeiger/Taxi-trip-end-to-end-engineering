import React, { useEffect, useState } from 'react';
import { Metrics } from '../components/Dashboard/Metrics';
import { RouteAnalyzer } from '../components/Dashboard/RouteAnalyzer';

export const DriverDashboard: React.FC = () => {
  const [metricsData, setMetricsData] = useState<any[]>([]);
  const [routes, setRoutes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch driver data
    const fetchData = async () => {
      try {
        // Placeholder for actual data fetching
        setMetricsData([
          { date: 'Mon', rides: 12, revenue: 450 },
          { date: 'Tue', rides: 15, revenue: 520 },
          { date: 'Wed', rides: 10, revenue: 380 },
        ]);
        setRoutes([
          {
            id: '1',
            pickup: 'Downtown',
            dropoff: 'Airport',
            efficiency: 92,
            avgTime: 35,
            avgPrice: 12.5,
          },
        ]);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch driver data:', error);
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  return (
    <div className="driver-dashboard">
      <h1>Driver Dashboard</h1>
      <Metrics data={metricsData} loading={loading} />
      <RouteAnalyzer routes={routes} />
    </div>
  );
};