import React, { useState, useEffect } from 'react';
import { Input } from '../components/UI/Input';
import { Button } from '../components/UI/Button';
import { RideCard } from '../components/Ride/RideCard';
import { useRide } from '../hooks/useRide';
import { ChatBot } from '../components/LLM/ChatBot';
import { RouteRecommendation } from '../components/LLM/RouteRecommendation';
import { MessageCircle } from 'lucide-react';

export const RideBooking: React.FC = () => {
  // Component state
  const [pickupLocation, setPickupLocation] = useState('');
  const [dropoffLocation, setDropoffLocation] = useState('');
  const [pickupAddress, setPickupAddress] = useState('');
  const [dropoffAddress, setDropoffAddress] = useState('');
  const { rides, loading, requestRide } = useRide();
  
  // Chat and Recommendation state
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [routeContext, setRouteContext] = useState<any>(null);

  // Update route context when both locations are selected
  useEffect(() => {
    if (pickupAddress && dropoffAddress) {
      setRouteContext({ 
        pickup: pickupAddress, 
        drop: dropoffAddress 
      });
    }
  }, [pickupAddress, dropoffAddress]);

  const handleBookRide = async () => {
    await requestRide({
      userId: 'user123',
      pickupLat: -6.2088,
      pickupLng: 106.8456,
      dropoffLat: -6.2146,
      dropoffLng: 106.8272,
    });
  };

  const handleSelectRoute = (pickupAddr: string, dropAddr: string) => {
    // Auto-fill addresses
    setPickupLocation(pickupAddr);
    setDropoffLocation(dropAddr);
    setPickupAddress(pickupAddr);
    setDropoffAddress(dropAddr);
    
    // If you have geocoding, you can convert addresses to coordinates here
    // This would update the map view
    console.log('Route selected:', { pickupAddr, dropAddr });
  };

  return (
    <div className="relative min-h-screen bg-gray-50">
      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-6">Book Your Ride</h1>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Booking Form */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white rounded-xl shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4">Trip Details</h2>
              <div className="space-y-4">
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
                <Button onClick={handleBookRide} loading={loading} className="w-full">
                  Find Rides
                </Button>
              </div>
            </div>

            {/* Available Rides Section */}
            {rides.length > 0 && (
              <div className="bg-white rounded-xl shadow-md p-6">
                <h2 className="text-xl font-semibold mb-4">Available Rides</h2>
                <div className="space-y-3">
                  {rides.map(ride => (
                    <RideCard
                      key={ride.id}
                      ride={ride as any}
                      onSelect={() => console.log('Selected:', ride)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* AI Route Recommendation Component */}
            <div className="mt-4">
              <RouteRecommendation onSelectRoute={handleSelectRoute} />
            </div>
          </div>

          {/* Right Column - Map or Additional Info */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-md p-6 sticky top-6">
              <h3 className="font-semibold text-lg mb-3">Quick Tips</h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li>✨ Try our AI recommendation to find the best route</li>
                <li>💬 Ask the chatbot for travel tips</li>
                <li>🚗 Compare prices across different ride types</li>
                <li>⭐ Share your ride code with friends</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Floating Chat Button */}
      <button
        onClick={() => setIsChatOpen(true)}
        className="fixed bottom-6 right-6 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 transition-all duration-200 z-40 hover:scale-110"
      >
        <MessageCircle size={24} />
      </button>

      {/* ChatBot Component */}
      <ChatBot 
        isOpen={isChatOpen} 
        onClose={() => setIsChatOpen(false)} 
        routeContext={routeContext}
      />
    </div>
  );
};