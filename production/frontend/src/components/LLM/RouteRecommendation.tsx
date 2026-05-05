import React, { useState } from 'react';
import { Sparkles, MapPin, Navigation, Clock, DollarSign } from 'lucide-react';
import { llmAPI } from '../../services/llmAPI';
import { Button } from '../UI/Button';

interface RouteRecommendationProps {
  onSelectRoute?: (pickup: string, drop: string) => void;
}

export const RouteRecommendation: React.FC<RouteRecommendationProps> = ({ onSelectRoute }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [recommendation, setRecommendation] = useState<any>(null);
  const [error, setError] = useState('');

  const getRecommendation = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    try {
      const result = await llmAPI.recommendRoute(query);
      setRecommendation(result);
    } catch (err: any) {
      setError(err.message || 'Failed to get recommendation');
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = () => {
    if (recommendation?.pickup && recommendation?.drop && onSelectRoute) {
      onSelectRoute(recommendation.pickup, recommendation.drop);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow p-5">
      <h3 className="text-lg font-semibold flex items-center gap-2 mb-3">
        <Sparkles size={20} className="text-green-500" />
        AI Route Recommender
      </h3>
      <p className="text-sm text-gray-500 mb-3">
        Describe where you want to go (e.g., "I want to go from the airport to the city center around 8 PM")
      </p>
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g., best route from Senayan to Kemang avoiding toll"
          className="flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
          onKeyPress={(e) => e.key === 'Enter' && getRecommendation()}
        />
        <Button onClick={getRecommendation} loading={loading} variant="primary">
          Recommend
        </Button>
      </div>

      {error && <p className="text-red-500 text-sm mt-2">{error}</p>}

      {recommendation && (
        <div className="mt-4 p-3 bg-gray-50 rounded-lg">
          {recommendation.error ? (
            <p className="text-red-500">{recommendation.error}</p>
          ) : (
            <>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm">
                  <MapPin size={16} className="text-green-500" />
                  <span><strong>Pickup:</strong> {recommendation.pickup || 'N/A'}</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Navigation size={16} className="text-red-500" />
                  <span><strong>Drop:</strong> {recommendation.drop || 'N/A'}</span>
                </div>
                {recommendation.vehicle_type && (
                  <div className="text-sm"><strong>Vehicle:</strong> {recommendation.vehicle_type}</div>
                )}
                {recommendation.reason && (
                  <div className="text-sm text-gray-600"><strong>Why:</strong> {recommendation.reason}</div>
                )}
                {recommendation.ml_estimated_time && (
                  <div className="flex items-center gap-2 text-sm">
                    <Clock size={16} />
                    <span>ETA: {recommendation.ml_estimated_time} min</span>
                  </div>
                )}
                {recommendation.ml_estimated_price && (
                  <div className="flex items-center gap-2 text-sm">
                    <DollarSign size={16} />
                    <span>Price: Rp {recommendation.ml_estimated_price.toLocaleString()}</span>
                  </div>
                )}
              </div>
              <button
                onClick={handleSelect}
                className="mt-3 w-full bg-green-500 text-white py-2 rounded-lg hover:bg-green-600 transition"
              >
                Use This Route
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
};