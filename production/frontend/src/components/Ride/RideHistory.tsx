import React, { useEffect, useState } from 'react';
import { RideCard } from './RideCard';

interface HistoryRide {
  id: string;
  driverName: string;
  date: string;
  status: 'completed' | 'cancelled';
  rating: number;
  price: number;
}

interface RideHistoryProps {
  userId: string;
}

export const RideHistory: React.FC<RideHistoryProps> = ({ userId }) => {
  const [rides, setRides] = useState<HistoryRide[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch ride history
    const fetchHistory = async () => {
      try {
        // const response = await api.getRideHistory(userId);
        // setRides(response.data);
        setLoading(false);
      } catch (error) {
        console.error('Failed to fetch ride history:', error);
        setLoading(false);
      }
    };

    fetchHistory();
  }, [userId]);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="ride-history">
      <h2>Ride History</h2>
      <div className="history-list">
        {rides.map(ride => (
          <div key={ride.id} className="history-item">
            <p>{ride.driverName}</p>
            <p>{ride.date}</p>
            <span className={ride.status}>{ride.status}</span>
            <span className="price">${ride.price}</span>
          </div>
        ))}
      </div>
    </div>
  );
};