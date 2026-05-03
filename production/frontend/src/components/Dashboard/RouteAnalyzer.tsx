import React, { useState } from 'react';

interface Route {
  id: string;
  pickup: string;
  dropoff: string;
  efficiency: number;
  avgTime: number;
  avgPrice: number;
}

interface RouteAnalyzerProps {
  routes: Route[];
}

export const RouteAnalyzer: React.FC<RouteAnalyzerProps> = ({ routes }) => {
  const [selectedRoute, setSelectedRoute] = useState<Route | null>(null);

  return (
    <div className="route-analyzer">
      <h2>Route Analysis</h2>
      <div className="routes-list">
        {routes.map(route => (
          <div 
            key={route.id} 
            className="route-item"
            onClick={() => setSelectedRoute(route)}
          >
            <p>{route.pickup} → {route.dropoff}</p>
            <p>Efficiency: {route.efficiency}%</p>
          </div>
        ))}
      </div>
      {selectedRoute && (
        <div className="route-details">
          <h3>{selectedRoute.pickup} → {selectedRoute.dropoff}</h3>
          <p>Avg Time: {selectedRoute.avgTime} min</p>
          <p>Avg Price: ${selectedRoute.avgPrice}</p>
        </div>
      )}
    </div>
  );
};