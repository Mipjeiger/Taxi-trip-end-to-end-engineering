import pandas as pd
import numpy as np
import pickle
from typing import Dict, Optional
from pathlib import Path
from tensorflow.keras.models import load_model
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class MLPredictor:
    """
    Unified ML Predictor for Taxi Trip predictions.
    
    Models Used:
    ├── CTAT (Customer Time to Arrival) - Regression
    │   ├── best_model_ctat_ultra.pkl (XGBoost/LightGBM - PRIMARY)
    │   └── model_time_improved.keras (TensorFlow - FALLBACK)
    │
    └── VTAT (Vehicle Time to Arrival) - Regression
        ├── best_model_vtat_ultra.pkl (XGBoost/LightGBM - PRIMARY)
        └── model_price_improved.keras (TensorFlow - FALLBACK)
    """
    def __init__(self):
        self.models_path = Path(__file__).parent.parent.parent / "models"
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.location_maps = {}
        self.features_list = None
        self.is_loaded = False

    async def load_models(self):
        """Load ML models and preprocessing objects."""
        try:
            logger.info(f"Loading models from {self.models_path}")

            # Primary models (XGBoost/LightGBM - Machine Learning models)
            ctat_path = self.models_path / "best_model_ctat_ultra.pkl"
            vtat_path = self.models_path / "best_model_vtat_ultra.pkl"

            if ctat_path.exists() and vtat_path.exists():
                self.models['ctat_primary'] = pickle.load(open(ctat_path, 'rb'))
                self.models['vtat_primary'] = pickle.load(open(vtat_path, 'rb'))
                logger.info("✅ Loaded primary ML models (XGBoost/LightGBM)")
            else:
                logger.warning("⚠️ Primary ML models not found. Will attempt to load fallback TensorFlow models.")
            
            # Fallback models (Return to TensorFlow models - for deployment redundancy)
            time_nn_path = self.models_path / "model_time_improved.keras"
            price_nn_path = self.models_path / "model_price_improved.keras"

            if time_nn_path.exists() and price_nn_path.exists():
                self.models['ctat_fallback'] = load_model(time_nn_path)
                self.models['vtat_fallback'] = load_model(price_nn_path)
                logger.info("✅ Loaded fallback TensorFlow models")
            else:
                logger.warning("⚠️ Fallback TensorFlow models not found. Prediction will fail if primary models are missing.")

            # Scalers
            scaler_ultra_path = self.models_path / "scaler_ultra.pkl"
            scaler_minmax_path = self.models_path / "scaler_minmax.pkl"

            if scaler_ultra_path.exists():
                self.scalers['ultra'] = pickle.load(open(scaler_ultra_path, 'rb'))
                logger.info("✅ Loaded ultra scaler for ML models")
            if scaler_minmax_path.exists():
                self.scalers['minmax'] = pickle.load(open(scaler_minmax_path, 'rb'))
                logger.info("✅ Loaded minmax scaler for NN models")

            # Encoders data
            pickup_encoder_path = self.models_path / "le_pickup.pkl"
            drop_encoder_path = self.models_path / "le_drop.pkl"

            if pickup_encoder_path.exists():
                self.encoders['pickup'] = pickle.load(open(pickup_encoder_path, 'rb'))
                self.encoders['drop'] = pickle.load(open(drop_encoder_path, 'rb'))
                logger.info("✅ Loaded location encoders")
            else:
                logger.warning("⚠️ Location encoders not found. Will use fallback encoding logic.")

            # Feature list (to ensure consistent feature order)
            features_path = self.models_path / "features_ultra.pkl"
            if features_path.exists():
                self.features = pickle.load(open(features_path, 'rb'))
                logger.info(f"Loaded feature list: {len(self.features)} features")
            else:
                logger.error("❌ Feature list not found. Prediction will fail without it.")
                raise FileNotFoundError("Feature list is required for prediction but was not found.")
            
            # Mark as loaded
            self.is_loaded = True
            logger.info("✅ All models and preprocessing objects loaded successfully.")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error loading models: {e}")
            self.is_loaded = False
            return False

    async def predict_ride_metrics(
            self, 
            pickup: str, 
            drop: str, 
            vehicle_type: str,
            hour: int, 
            day_of_week: int, 
            distance_km: float,
            booking_datetime: None,
            demand_pressure: float = 1.0,
            rating_avg: float = 4.5,
            use_fallback: bool = False
    ) -> Dict:
        """ 
        Predict ride metrics (CTAT, VTAT, price, completion time).
    
        Args:
            pickup: Pickup location name
            drop: Dropoff location name
            vehicle_type: Vehicle type (Auto, Car, Go Sedan, Motorcycle, Premier Sedan, eBike, Uber XL)
            hour: Hour of day (0-23)
            day_of_week: Day of week (0=Monday, 6=Sunday)
            distance_km: Distance in kilometers
            booking_datetime: When ride was booked (defaults to now)
            demand_pressure: Demand pressure value (170-777 from database)
            rating_avg: Average driver+customer rating (3.8-5.0)
            use_fallback: Force use of fallback models
        
        Returns:
            Dict with predictions including estimated_completed_at"""
        if not self.is_loaded:
            raise RuntimeError("Models not loaded. Call load_models() first.")
        
        try:
            # Pre-compute time-based features before extracting model features
            is_peak_hour = 1 if (7 <= hour <= 9) or (17 <= hour <= 19) else 0
            is_night = 1 if hour >= 22 or hour < 5 else 0

            # Extract and scale features
            features_df = await self._extract_features(
                pickup, drop, vehicle_type, hour, day_of_week, distance_km
            )

            # Predict CTAT (Customer Time to Arrival)
            ctat_pred = await self._predict_ctat(features_df, use_fallback)

            # Predict VTAT (Vehicle Time to Arrival)
            vtat_pred = await self._predict_vtat(features_df, use_fallback)

            # Calculate derived metrics
            total_time = ctat_pred + vtat_pred

            # Calculate price with database informed logic
            estimated_price = await self._calculate_price(
                distance_km=distance_km,
                time_min=total_time,
                vehicle_type=vehicle_type,
                is_peak_hour=is_peak_hour,
                is_night=is_night,
                demand_pressure=demand_pressure,
                rating_avg=rating_avg
            )

            # Predict completion timestamp
            completed_at = await self.predict_completed_at(booking_datetime, ctat_pred)

            # VTAT prediction to ensure the vehicle pickup time is reasonable
            vehicle_arrival_at = await self.predict_vehicle_arrival(booking_datetime, vtat_pred)
            vehicle_arrival_status = await self._calculate_vehicle_arrival_status(vtat_pred)
            
            # Return prediction into dictionary format
            return {
                "pickup_location": pickup,
                "drop_location": drop,
                "vehicle_type": vehicle_type,
                "distance_km": round(distance_km, 2),
                "booking_datetime": booking_datetime.isoformat(),
                "estimated_pickup_time_minute": round(vtat_pred, 2),
                "estimated_drop_time_minute": round(ctat_pred, 2),
                "total_ride_time_minute": round(total_time, 2),
                "estimated_completed_at": completed_at.isoformat(),
                "estimated_price_idr": round(estimated_price, 2),
                "estimated_vehicle_arrival_at": vehicle_arrival_at.isoformat(),
                "estimated_vehicle_arrival_minute": round(vtat_pred, 2),
                "vehicle_arrival_status": vehicle_arrival_status,
                "price_per_km": round(estimated_price / distance_km, 2) if distance_km > 0 else 0,
                "average_speed_kmh": round(distance_km / (total_time / 60), 2) if total_time > 0 else 0,
                "is_peak_hour": bool(is_peak_hour),
                "demand_pressure": round(demand_pressure, 2),
                "rating_avg": round(rating_avg, 2),
                "model_confidence": "high" if not use_fallback else "medium"
            }
        
        except Exception as e:
            logger.error(f"❌ Error during prediction: {str(e)}")
            raise e

    async def _extract_features(
            self, 
            pickup: str, 
            drop: str, 
            vehicle_type: str,
            hour: int, 
            day_of_week: int, 
            distance_km: float
    ) -> pd.DataFrame:
        """Extract features matching training pipeline exactly."""

        # Encode locations with fallback for unseen values
        try:
            pickup_encoded = self.encoders['pickup'].transform([pickup])[0]
        except Exception as e:
            logger.warning(f"⚠️ Pickup encoding failed for '{pickup}': {e}, using fallback encoding.")
            pickup_encoded = hash(pickup) % 1000

        try:
            drop_encoded = self.encoders['drop'].transform([drop])[0]
        except Exception as e:
            logger.warning(f"⚠️ Drop encoding failed for '{drop}': {e}, using fallback encoding.")
            drop_encoded = hash(drop) % 1000

        # Route clustering logic
        route_key = f"{pickup_encoded}_{drop_encoded}"
        route_cluster = hash(route_key) % 100

        # Vehicle type encoding
        VEHICLE_TYPE_ENCODING = {
            'Auto': 0,
            'Car': 1,
            'Go Sedan': 2,
            'Motorcycle': 3,
            'Premier Sedan': 4,
            'eBike': 5,
            'Uber XL': 6,
        }
        vehicle_encoded = VEHICLE_TYPE_ENCODING.get(vehicle_type, 0)
        logger.info(f"Encoded vehicle type '{vehicle_type}' as {vehicle_encoded}")

        # Time-based features
        is_peak_hour = 1 if (7 <= hour <= 9) or (17 <= hour <= 19) else 0
        is_weekend = 1 if day_of_week >= 5 else 0
        is_night = 1 if hour >= 22 or hour < 5 else 0

        # Cyclical encoding for hour and day
        hour_sin = np.sin(2 * np.pi * hour / 24)
        hour_cos = np.cos(2 * np.pi * hour / 24)
        day_sin = np.sin(2 * np.pi * day_of_week / 7)
        day_cos = np.cos(2 * np.pi * day_of_week / 7)

        # Create feature dictionary and DataFrame
        feature_dict = {
            'Pickup Encoded': pickup_encoded,
            'Drop Encoded': drop_encoded,
            'Vehicle Type Encoded': vehicle_encoded,
            'hour': hour,
            'day_of_week': day_of_week,
            'route_cluster': route_cluster,
            'Ride Distance': distance_km,
            'is_peak_hour': is_peak_hour,
            'is_weekend': is_weekend,
            'is_night': is_night,
            'hour_sin': hour_sin,
            'hour_cos': hour_cos,
            'day_sin': day_sin,
            'day_cos': day_cos,
        }
        df = pd.DataFrame([feature_dict])

        # Ensure all expected features exist (fill missing with 0)
        for col in self.features:
            if col not in df.columns:
                df[col] = 0
            
        # Return features in exact training order
        return df[self.features]
    
    async def _predict_ctat(self, features_df: pd.DataFrame, use_fallback: bool = False) -> float:
        """Predict CTAT using primary or fallback model."""
        try:
            if not use_fallback and 'ctat_primary' in self.models:
                # Use ML model are trained
                features_scaled = self.scalers['ultra'].transform(features_df)
                ctat = float(self.models['ctat_primary'].predict(features_scaled)[0])
            elif 'ctat_fallback' in self.models:
                # Use fallback NN model
                features_scaled = self.scalers['minmax'].transform(features_df)
                ctat = float(self.models['ctat_fallback'].predict(features_scaled, verbose=0)[0])
            else:
                logger.warning("⚠️ No CTAT model available for prediction.")
                ctat = 20.0  # Default fallback value

            return max(ctat, 5.0) # Ensure minimum CTAT of 5 minutes
        
        except Exception as e:
            logger.error(f"❌ CTAT prediction error: {e}")
            return 20.0
        
    async def _predict_vtat(self, features_df: pd.DataFrame, use_fallback: bool = False) -> float:
        """Predict VTAT using primary or fallback model."""
        try:
            if not use_fallback and 'vtat_primary' in self.models:
                # Use ML model are trained
                features_scaled = self.scalers['ultra'].transform(features_df)
                vtat = float(self.models['vtat_primary'].predict(features_scaled)[0])
            elif 'vtat_fallback' in self.models:
                # Use fallback NN model
                features_scaled = self.scalers['minmax'].transform(features_df)
                vtat = float(self.models['vtat_fallback'].predict(features_scaled, verbose=0)[0])
            else:
                logger.warning("⚠️ No VTAT model available for prediction.")
                vtat = 10.0  # Default fallback value

            return max(vtat, 2.0) # Ensure minimum VTAT of 2 minutes
        
        except Exception as e:
            logger.error(f"❌ VTAT prediction error: {e}")
            return 10.0

    async def _calculate_price(
            self, 
            distance_km: float, 
            time_min: float, 
            vehicle_type: str = "Car",
            is_peak_hour: int = 0,
            is_night: int = 0,
            demand_pressure: float = 1.0,
            rating_avg: float = 4.5
    ) -> float:
        """Calculate price basde on database features.
        
        Database reference:
        - 'Booking Value': 99000-571000 IDR (actual prices)
        - 'price_per_km': 2599-17380 IDR/km (varies by vehicle/demand)
        - Vehicle Type distribution affects base rates
        - Demand pressure range: 170-777 (normalized to 1.0+)
        - Rating range: 3.8-5.0
        """
        try:
            # Vehhicle type base multipliers (from database booking value averages)
            vehicle_multiplier = {
                "Auto": 0.85, # Base vehicle
                "Car": 1.0, # Standard baseline
                "Go Sedan": 1.25, # Premium option
                "Motorcycle": 0.70, # Budget option
                "Premier Sedan": 1.5, # Luxury option
                "eBike": 0.55, # Economy friendly option
                "Uber XL": 1.35 # Large capacity option
            }
            vehicle_mult = vehicle_multiplier.get(vehicle_type, 1.0)

            # Base rate per km (derived from database average price per km)
            # Information: 2599-13780, normalized to 3000-15000 for calculation
            base_price_per_km = 2800 # IDR/km

            # Calculate base price from distance
            distance_price = distance_km * base_price_per_km * vehicle_mult

            # Time component (from database: total_time affects price)
            # Derived from: Booking Value / total_time shows ~1000-2000 IDR per minute range
            time_price = time_min * 150

            # Fixed base fare comment
            base_fare = 15000
            
            # Demand surge multiplier - Database demand_pressure range: 170-777, normalized to 0.8-1.8 multiplier
            demand_surge = 1.0 * ((demand_pressure - 250) / 500)
            demand_surge = max(0.8, min(demand_surge, 1.8)) # Clamp to 0.8-1.8 range

            # Peak hour surge
            peak_surge = 1.35 if is_peak_hour else 1.0

            # Night hour surge
            night_surge = 1.25 if is_night else 1.0

            # Rating quality factor (high rating = stable, low rating = surge)
            # Database rating range: 3.8-5.0
            rating_factor = 1.0 - ((5.0 - rating_avg) * 0.08)
            rating_factor = max(0.9, min(rating_factor, 1.5))

            # Composite price calculation
            final_price = (base_fare + distance_price + time_price) * \
                            peak_surge * night_surge * demand_surge * rating_factor
            
            # Apply minimum and maximum bounds
            min_fare = 20000 # Minimum fare based on database lowest booking value
            max_fare = 1000000 # Maximum fare based on database highest booking value

            return max(min_fare, min(final_price, max_fare))
        
        except Exception as e:
            logger.error(f"❌ Price calculation error: {e}")
            return 50000 # Default fallback price
        
    async def _calculate_vehicle_arrival_status(self, vtat_minutes: float) -> str:
        """
        Calculate vehicle arrival status based on VTAT prediction.
        
        Status levels:
        - "arriving_soon": VTAT < 5 min (vehicle nearly at pickup)
        - "arriving": 5-15 min (vehicle on the way)
        - "coming": 15-30 min (normal pickup time)
        - "delayed": >= 30 min (longer than expected)
        """
        try:
            vtat = float(vtat_minutes)
        
            if vtat < 5:
                status = "arriving_soon"
            elif vtat < 15:
                status = "arriving"
            elif vtat < 30:
                status = "coming"
            else:
                status = "delayed"

            logger.info(f"Vehicle arrival status based on VTAT {vtat:.1f} min: {status}")
            return status
        except Exception as e:
            logger.error(f"❌ Error calculating vehicle arrival status: {e}")
            return "coming"
        
    async def predict_completed_at(
            self,
            booking_datetime: datetime,
            ctat_minutes: float
    ) -> datetime:
        """
        Predict ride completion timestamp.
        
        Formula: completed_at = booking_datetime + CTAT
        
        Database reference:
        - 'Datetime': Booking timestamp
        - 'Avg CTAT': Completion time in minutes (15.1-39.9 range)
        - Completed time = Booking time + CTAT duration
        
        Args:
            booking_datetime: When ride was booked
            ctat_minutes: Predicted CTAT from model
            
        Returns:
            datetime: Predicted ride completion timestamp"""
        try:
            # CTAT represents total ride duration
            completed_at = booking_datetime + timedelta(minutes=float(ctat_minutes))

            logger.info(f"✅ Predicted completion: {booking_datetime} + {ctat_minutes:.1f} min = {completed_at}")
            return completed_at
        
        except Exception as e:
            logger.error(f"❌ Error predicting completion time: {e}")
            return booking_datetime + timedelta(minutes=30) # Default fallback completion time
        
    async def predict_vehicle_arrival(
            self,
            booking_datetime: datetime,
            vtat_minutes: float
    ) -> datetime:
        """
        Predict vehicle arrival timestamp at pickup location.
        
        Formula: vehicle_arrival_at = booking_datetime + VTAT
        
        Args:
            booking_datetime: When ride was booked
            vtat_minutes: Predicted VTAT from model
            
        Returns:
            datetime: Predicted vehicle arrival timestamp
        """
        try:
            vehicle_arrival_at = booking_datetime + timedelta(minutes=float(vtat_minutes))
            logger.info(f"✅ Vehicle arrives at pickup: {vehicle_arrival_at}")
            return vehicle_arrival_at
        except Exception as e:
            logger.error(f"❌ Error predicting vehicle arrival time: {e}")
            return booking_datetime + timedelta(minutes=10)