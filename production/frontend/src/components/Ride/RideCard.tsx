import React from 'react';

interface RideData {
    id: string;
    driverName: string;
    rating: number;
    vehicleType: string;
    estimatedPrice: number;
    estimatedTime: number;
    distance: number;
}

interface RideCardProps {
    ride: RideData;
    onSelect: (rideId: string) => void;
}

export const RideCard: React.FC<RideCardProps> = ({ ride, onSelect }) => {
    return (
    <div className="ride-card" onClick={() => onSelect(ride.id)}>
      <div className="ride-header">
        <h3>{ride.driverName}</h3>
        <span className="rating">⭐ {ride.rating}</span>
      </div>
      <div className="ride-details">
        <p>Vehicle: {ride.vehicleType}</p>
        <p>Distance: {ride.distance} km</p>
        <p>Time: {ride.estimatedTime} min</p>
      </div>
      <div className="ride-footer">
        <span className="price">${ride.estimatedPrice}</span>
        <button onClick={(e) => { e.stopPropagation(); onSelect(ride.id); }}>
          Select
        </button>
      </div>
    </div>
  );
};