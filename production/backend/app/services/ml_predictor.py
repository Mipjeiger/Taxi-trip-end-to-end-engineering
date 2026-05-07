import pandas as pd
import numpy as np
import pickle
from typing import Dict
from pathlib import Path
from tensorflow.keras.models import load_model
import logging

logger = logging.getLogger(__name__)

class MLPredictor:
    def __init__(self):
        self.models_path = Path(__file__).parent.parent.parent / "models"
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.location_maps = {}
        self.features = None

    async def load_models(self):
        """Load ML models and preprocessing objects."""
        try:
            # CTAT and VTAT models (Machine Learning models)
            self.models['ctat'] = pickle.load(open(self.models_path / "best_model_ctat_ultra.pkl", "rb"))
            self.models['vtat'] = pickle.load(open(self.models_path / "best_model_vtat_ultra.pkl", "rb"))
            
            # Neural network models for price and time (if used)
            self.models['price'] = load_model(self.models_path / "model_price_improved.keras")
            self.models['time'] = load_model(self.models_path / "model_time_improved.keras")

            # Scalers
            self.scalers['standard'] = pickle.load(open(self.models_path / "scaler.pkl", 'rb'))
            self.scalers['minmax'] = pickle.load(open(self.models_path / "scaler_minmax.pkl", 'rb'))
            self.scalers['ultra'] = pickle.load(open(self.models_path / "scaler_ultra.pkl", 'rb'))
            
            # Label encoders for locations
            self.encoders['pickup'] = pickle.load(open(self.models_path / "le_pickup.pkl", 'rb'))
            self.encoders['drop'] = pickle.load(open(self.models_path / "le_drop.pkl", 'rb'))
            
            # Location maps (for reverse mapping if needed)
            self.location_maps['pickup'] = pickle.load(open(self.models_path / "pickup_location_map.pkl", 'rb'))
            self.location_maps['drop'] = pickle.load(open(self.models_path / "drop_location_map.pkl", 'rb'))
            
            # List of all features used during training
            self.features = pickle.load(open(self.models_path / "features_ultra.pkl", 'rb'))

            logger.info("All models and preprocessing objects loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            raise e

    async def predict_ride_metrics(self, pickup: str, drop: str, vehicle_type: str,
                                   hour: int, day_of_week: int, distance_km: float) -> Dict:
        """Predict ride metrics using ML models and return formatted result."""
        # Extract feature vector
        features = await self._extract_features(pickup, drop, vehicle_type, hour, day_of_week, distance_km)
        features_scaled = self.scalers['ultra'].transform(features)

        # Predict CTAT (customer time to destination) and VTAT (vehicle time to pickup)
        ctat_pred = float(self.models['ctat'].predict(features_scaled)[0])
        vtat_pred = float(self.models['vtat'].predict(features_scaled)[0])
        total_time = ctat_pred + vtat_pred

        # Use provided distance_km (should come from maps API)
        distance = distance_km

        # Predict price (option 1: using neural network)
        # price_pred = float(self.models['price'].predict(features_scaled)[0][0])
        # Option 2: use heuristic formula (as fallback)
        price = await self._calculate_price(distance, total_time, 
                                            features['is_peak_hour'].iloc[0] if 'is_peak_hour' in features else 0)

        return {
            'pickup_location': pickup,
            'drop_location': drop,
            'distance_km': round(distance, 2),
            'estimated_pickup_time_minute': round(total_time, 2),
            'estimated_drop_time_minute': round(cta,
            'vtat_min': round(vtat_pred, 2),
            'ctat_min': round(ctat_pred, 2),
            'estimated_price_idr': round(price, 2),
            'average_speed_kmh': round(distance / (total_time / 60), 2) if total_time > 0 else 0,
            'price_per_km': round(price / distance, 2) if distance > 0 else 0,
            'vehicle_type': vehicle_type,
        }

    async def _extract_features(self, pickup: str, drop: str, vehicle_type: str,
                                hour: int, day_of_week: int, distance_km: float) -> pd.DataFrame:
        """Extract and preprocess features for prediction."""
        # Encode locations with fallback for unseen values
        try:
            pickup_encoded = self.encoders['pickup'].transform([pickup])[0]
        except:
            pickup_encoded = 0  # fallback
        try:
            drop_encoded = self.encoders['drop'].transform([drop])[0]
        except:
            drop_encoded = 0

        # Route cluster (simplified)
        route_key = f"{pickup_encoded}_{drop_encoded}"
        route_cluster = hash(route_key) % 100

        # Vehicle type encoding
        vehicle_map = {'Car': 1, 'Bike': 0, 'Auto': 2}
        vehicle_encoded = vehicle_map.get(vehicle_type, 1)

        feature_dict = {
            'Pickup Encoded': pickup_encoded,
            'Drop Encoded': drop_encoded,
            'Vehicle Type Encoded': vehicle_encoded,
            'hour': hour,
            'day_of_week': day_of_week,
            'route_cluster': route_cluster,
            'Ride Distance': distance_km,
            'is_peak_hour': 1 if (7 <= hour <= 9) or (17 <= hour <= 19) else 0,
            'is_weekend': 1 if day_of_week >= 5 else 0,
            'is_night': 1 if hour >= 22 or hour < 5 else 0,
            'hour_sin': np.sin(2 * np.pi * hour / 24),
            'hour_cos': np.cos(2 * np.pi * hour / 24),
            'day_sin': np.sin(2 * np.pi * day_of_week / 7),
            'day_cos': np.cos(2 * np.pi * day_of_week / 7),
        }

        df = pd.DataFrame([feature_dict])
        # Ensure all expected features exist (fill missing with 0)
        for col in self.features:
            if col not in df.columns:
                df[col] = 0
        return df[self.features]

    async def _calculate_price(self, distance_km: float, time_min: float, is_peak: int = 0) -> float:
        """Calculate price based on distance, time, and peak hour factor."""
        base_fare = 7000         # IDR
        per_km = 2900            # IDR per km
        per_min = 1200           # IDR per minute
        surge = 1.5 if is_peak else 1.0
        return (base_fare + distance_km * per_km + time_min * per_min) * surge