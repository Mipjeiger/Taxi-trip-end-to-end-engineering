import React, { useState } from 'react';
import { Sparkles, MapPin, Navigation, Clock, DollarSign, AlertCircle } from 'lucide-react';
import llmAPI, { RouteRecommendation as RouteType } from '../../services/llmAPI';  // Use default import
import { Button } from '../UI/Button';

interface RouteRecommendationProps {
  onSelectRoute?: (pickup: string, drop: string, vehicleType?: string) => void;
}

export const RouteRecommendation: React.FC<RouteRecommendationProps> = ({ onSelectRoute }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [recommendation, setRecommendation] = useState<any>(null);
  const [error, setError] = useState('');

  const getRecommendation = async () => {
    if (!query.trim()) {
      setError('Please describe where you want to go');
      return;
    }
    
    setLoading(true);
    setError('');
    setRecommendation(null);
    
    try {
      const result = await llmAPI.recommendRoute(query);
      setRecommendation(result);
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || 
                       err.message || 
                       'Failed to get recommendation. Please try again.';
      setError(errorMsg);
      console.error('Route recommendation error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = () => {
    if (recommendation?.pickup && recommendation?.drop) {
      if (onSelectRoute) {
        onSelectRoute(
          recommendation.pickup,
          recommendation.drop,
          recommendation.vehicle_type || 'Car'
        );
      }
    } else {
      setError('Please get a valid recommendation first');
    }
  };

  const hasRecommendation = recommendation && !recommendation.error;

  return (
    <div className="bg-white rounded-xl shadow p-5">
      <h3 className="text-lg font-semibold flex items-center gap-2 mb-3">
        <Sparkles size={20} className="text-green-500" />
        AI Route Recommender
      </h3>
      
      <p className="text-sm text-gray-600 mb-4">
        Describe where you want to go (e.g., "I want to go from the airport to the city center around 8 PM")
      </p>
      
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g., best route from Senayan to Kemang avoiding toll"
          className="flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
          onKeyPress={(e) => e.key === 'Enter' && !loading && getRecommendation()}
          disabled={loading}
        />
        <Button 
          onClick={getRecommendation} 
          loading={loading} 
          variant="primary"
          disabled={loading}
        >
          Recommend
        </Button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="flex gap-2 items-start p-3 bg-red-50 border border-red-200 rounded-lg mb-3">
          <AlertCircle size={16} className="text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Recommendation Display */}
      {hasRecommendation && (
        <div className="mt-4 p-4 bg-gradient-to-br from-green-50 to-blue-50 rounded-lg border border-green-200">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <MapPin size={18} className="text-green-500 flex-shrink-0" />
              <div className="text-sm">
                <span className="font-semibold">From:</span> {recommendation.pickup || 'N/A'}
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <Navigation size={18} className="text-red-500 flex-shrink-0" />
              <div className="text-sm">
                <span className="font-semibold">To:</span> {recommendation.drop || 'N/A'}
              </div>
            </div>

            {recommendation.vehicle_type && (
              <div className="text-sm">
                <span className="font-semibold">Vehicle:</span> {recommendation.vehicle_type}
              </div>
            )}

            {recommendation.reason && (
              <div className="text-sm bg-white p-2 rounded border-l-2 border-green-500">
                <span className="font-semibold">Why:</span> {recommendation.reason}
              </div>
            )}

            {recommendation.estimated_time && (
              <div className="flex items-center gap-2 text-sm">
                <Clock size={16} className="text-blue-500" />
                <span><strong>ETA:</strong> {recommendation.estimated_time} min</span>
              </div>
            )}

            {recommendation.description && (
              <div className="text-sm italic text-gray-700">
                {recommendation.description}
              </div>
            )}
          </div>

          <button
            onClick={handleSelect}
            className="mt-4 w-full bg-green-500 text-white py-2 rounded-lg hover:bg-green-600 transition disabled:opacity-50"
            disabled={loading}
          >
            Use This Route
          </button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="mt-4 p-4 bg-blue-50 rounded-lg text-center">
          <div className="flex justify-center gap-1 mb-2">
            <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
            <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
            <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
          </div>
          <p className="text-sm text-gray-600">Getting recommendation...</p>
        </div>
      )}
    </div>
  );
};

export default RouteRecommendation;