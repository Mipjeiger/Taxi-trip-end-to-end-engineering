import React, { useState } from 'react';
import { RideRequest, RidePrediction } from '../../types';
import { api } from '../../services/api';
import { LoadingSpinner } from '../UI/LoadingSpinner';

interface PriceEstimatorProps {
    pickup: string;
    drop: string;
    onEstimateComplete: (prediction: RidePrediction) => void;
}

const PriceEstimator: React.FC<PriceEstimatorProps> = ({ 
    pickup, 
    drop, 
    onEstimateComplete }) => {
        const [loading, setLoading] = useState(false);
        const [vehicleType, setVehicleType] = useState<'Car' | 'Bike' | 'Auto'>('Car');
        const [prediction, setPrediction] = useState<RidePrediction | null>(null);

        const estimateRide = async () => {
            if (!pickup || !drop) {
                alert('Please select pickup and drop locations.');
                return;
        }

        setLoading(true);
        try {
            const request: RideRequest = {
                pickup_location: pickup,
                drop_location: drop,
                vehicle_type: vehicleType
            };

            const result = await api.predictRoute(request);
            setPrediction(result);
            onEstimateComplete(result);
        } catch (error) {
            console.error('Error estimating ride:', error);
            alert('Failed to estimate ride. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <h2 className="text-2xl font-bold mb-4">Ride Estimate</h2>
      
      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Vehicle Type</label>
        <div className="flex space-x-2">
          {['Car', 'Bike', 'Auto'].map((type) => (
            <button
              key={type}
              onClick={() => setVehicleType(type as any)}
              className={`px-4 py-2 rounded-lg ${
                vehicleType === type
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-200 text-gray-700'
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={estimateRide}
        disabled={loading || !pickup || !drop}
        className="w-full bg-green-500 text-white py-3 rounded-lg font-semibold hover:bg-green-600 transition disabled:bg-gray-300"
      >
        {loading ? <LoadingSpinner /> : 'Estimate Ride'}
      </button>

      {prediction && (
        <div className="mt-6 space-y-3">
          <div className="border-t pt-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Distance</span>
              <span className="font-semibold">{prediction.distance_km} km</span>
            </div>
            <div className="flex justify-between items-center mt-2">
              <span className="text-gray-600">Estimated Time</span>
              <span className="font-semibold">{prediction.estimated_time_min} min</span>
            </div>
            <div className="flex justify-between items-center mt-2">
              <span className="text-gray-600">Price</span>
              <span className="text-2xl font-bold text-green-600">
                Rp {prediction.estimated_price_idr.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between items-center mt-2 text-sm">
              <span className="text-gray-500">Avg Speed</span>
              <span>{prediction.average_speed_kmh} km/h</span>
            </div>
            <div className="flex justify-between items-center mt-2 text-sm">
              <span className="text-gray-500">Price per km</span>
              <span>Rp {prediction.price_per_km.toLocaleString()}</span>
            </div>
          </div>
          
          <button className="w-full bg-black text-white py-3 rounded-lg font-semibold hover:bg-gray-800 transition">
            Request {vehicleType}
          </button>
        </div>
      )}
    </div>
  );
};

export default PriceEstimator;