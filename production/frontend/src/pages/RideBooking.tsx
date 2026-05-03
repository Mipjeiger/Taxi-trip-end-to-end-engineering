import React, { useState } from 'react';
import { Input } from '../components/UI/Input';
import { Button } from '../components/UI/Button';
import { RideCard } from '../components/Ride/RideCard';
import { useRide } from '../hooks/useRide';

export const RideBooking: React.FC = () => {
  const [pickupLocation, setPickupLocation] = useState('');
  const [dropoffLocation, setDropoffLocation] = useState('');
  const { rides, loading, requestRide } = useRide();

  const handleBookRide = async () => {
    await requestRide({
      userId: 'user123',
      pickupLat: -6.2088,
      pickupLng: 106.8456,
      dropoffLat: -6.2146,
      dropoffLng: 106.8272,
    });
  };

  return (
    <div className="ride-booking-page">
      <h1>Book Your Ride</h1>
      <div className="booking-form">
        <Input
          label="Pickup Location"
          placeholder="Enter pickup location"
          value={pickupLocation}
          onChange={(e) => setPickupLocation(e.target.value)}
        />
        <Input
          label="Dropoff Location"
          placeholder="Enter dropoff location"
          value={dropoffLocation}
          onChange={(e) => setDropoffLocation(e.target.value)}
        />
        <Button onClick={handleBookRide} loading={loading}>
          Find Rides
        </Button>
      </div>
      <div className="available-rides">
        {rides.map(ride => (
          <RideCard
            key={ride.id}
            ride={ride}
            onSelect={() => console.log('Selected:', ride)}
          />
        ))}
      </div>
    </div>
  );
};