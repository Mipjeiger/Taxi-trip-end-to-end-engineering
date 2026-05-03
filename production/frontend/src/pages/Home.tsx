import React from 'react';
import { Button } from '../components/UI/Button';
import { RouteMap } from '../components/Map/RouteMap';

export const Home: React.FC = () => {
    const [pickup, setPickup] = React.useState({ lat: -6.2088, lng: 106.8456 });
    const [dropoff, setDropoff] = React.useState({ lat: -6.2146, lng: 106.8272 });

    return (
    <div className="home-page">
      <h1>Gojek Ride Booking</h1>
      <RouteMap pickup={pickup} dropoff={dropoff} />
      <div className="actions">
        <Button variant="primary" onClick={() => console.log('Book ride')}>
          Book Ride
        </Button>
      </div>
    </div>
  );
};