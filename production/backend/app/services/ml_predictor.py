import pandas as pd
import numpy as np
import pickle
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime, timedelta
from app.core.redis_client import redis_get, redis_set
from app.core.database import get_supabase_connection
from app.services.model_loader import ModelLoader
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
        self.models_path = Path("/app/models")
        if not self.models_path.exists():
            self.models_path = Path(__file__).parent.parent.parent / "models"  # Fallback for local development
        logger.info(f"Using models path: {self.models_path}")
        
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.location_maps = {}
        self.features = None
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
            
            """Later to add fallback Tensorflow models if needed for deployment redundancy - currently
                not included to save space and complexity."""
            
            # Fallback models (Return to TensorFlow models - for deployment redundancy)
            #time_nn_path = self.models_path / "model_time_improved.keras"
            #price_nn_path = self.models_path / "model_price_improved.keras"

            #if time_nn_path.exists() and price_nn_path.exists():
            #    self.models['ctat_fallback'] = load_model(time_nn_path)
            #    self.models['vtat_fallback'] = load_model(price_nn_path)
            #    logger.info("✅ Loaded fallback TensorFlow models")
            #else:
            #    logger.warning("⚠️ Fallback TensorFlow models not found. Prediction will fail if primary models are missing.")

            # Scalers
            scaler_ultra_path = self.models_path / "scaler_ultra.pkl"
            scaler_minmax_path = self.models_path / "scaler_minmax.pkl"

            if scaler_ultra_path.exists():
                self.scalers['ultra'] = pickle.load(open(scaler_ultra_path, 'rb'))
            if scaler_minmax_path.exists():
                self.scalers['minmax'] = pickle.load(open(scaler_minmax_path, 'rb'))

            # Encoders data
            pickup_encoder_path = self.models_path / "le_pickup.pkl"
            drop_encoder_path = self.models_path / "le_drop.pkl"

            if pickup_encoder_path.exists() and drop_encoder_path.exists():
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
            booking_datetime: Optional[datetime] = None,
            demand_pressure: float = 1.0,
            rating_avg: float = 4.5,
            use_fallback: bool = False,
            ride_id: Optional[str] = None
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
            ride_id: Optional ride ID for tracking
        Returns:
            Dict with predictions including estimated_completed_at"""
        if not self.is_loaded:
            raise RuntimeError("Models not loaded. Call load_models() first.")
        
        if booking_datetime is None:
            booking_datetime = datetime.now()
        
        try:
            # Pre-compute time-based features before extracting model features
            is_peak_hour = 1 if (7 <= hour <= 9) or (17 <= hour <= 19) else 0
            is_night = 1 if hour >= 22 or hour < 5 else 0

            # Extract and scale features
            features_df = await self._extract_features(
                pickup, drop, vehicle_type, hour, day_of_week, distance_km
            )

            # Predict CTAT (Customer Time to Arrival), VTAT (Vehicle Time to Arrival), and calculate price
            ctat_pred = await self._predict_ctat(features_df, use_fallback)
            vtat_pred = await self._predict_vtat(features_df, use_fallback)
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

            # Predict completion timestamp, vehicle arrival timestamp, and their respective statuses
            completed_at = await self.predict_completed_at(booking_datetime, ctat_pred)
            vehicle_arrival_at = await self.predict_vehicle_arrival(booking_datetime, vtat_pred)
            vehicle_arrival_status = await self._calculate_vehicle_arrival_status(vtat_pred)

            # Predict to get driver based on status -> TODO: define logic customer arrival status & driver status based on CTAT prediction and database insights
            customer_arrival_at = await self.predict_completed_at(booking_datetime, total_time)
            customer_arrival_status = await self._calculate_customer_arrival_status(ctat_pred)
            
            
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
                "customer_arrival_status": customer_arrival_status,
                "price_per_km": round(estimated_price / distance_km, 2) if distance_km > 0 else 0,
                "average_speed_kmh": round(distance_km / (total_time / 60), 2) if total_time > 0 else 0,
                "is_peak_hour": bool(is_peak_hour),
                "demand_pressure": round(demand_pressure, 2),
                "rating_avg": round(rating_avg, 2),
                "model_confidence": "high" if not use_fallback else "medium"
            }
        
        except Exception as e:
            logger.error(f"❌ Error during prediction: {str(e)}")
            raise

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
            pickup_encoded = -1

        try:
            drop_encoded = self.encoders['drop'].transform([drop])[0]
        except Exception as e:
            logger.warning(f"⚠️ Drop encoding failed for '{drop}': {e}, using fallback encoding.")
            drop_encoded = -1

        # Route clustering logic
        route_key = f"{pickup_encoded}_{drop_encoded}"
        route_cluster = hash(route_key) % 100

        # Vehicle type encoding
        VEHICLE_TYPE_ENCODING = {
           'Auto': 0, 'Car': 1, 'Go Sedan': 2,
            'Motorcycle': 3, 'Premier Sedan': 4, 'eBike': 5, 'Uber XL': 6
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
        for col in self.features:
            if col not in df.columns:
                df[col] = 0
    
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
            base_price_per_km = 2800 # IDR/km
            distance_price = distance_km * base_price_per_km * vehicle_mult
            time_price = time_min * 150
            base_fare = 15000
            demand_surge = 1.0 * ((demand_pressure - 250) / 500)
            demand_surge = max(0.8, min(demand_surge, 1.8)) # Clamp to 0.8-1.8 range
            peak_surge = 1.35 if is_peak_hour else 1.0
            night_surge = 1.25 if is_night else 1.0
            rating_factor = 1.0 - ((5.0 - rating_avg) * 0.08)
            rating_factor = max(0.9, min(rating_factor, 1.5))
            final_price = (base_fare + distance_price + time_price) * \
                            peak_surge * night_surge * demand_surge * rating_factor
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
            return booking_datetime + timedelta(minutes=30)
        
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

    async def _get_ride_distance(self, ride_id: str) -> float:
        """
        FIX: Query analytics.trip (distance_km) instead of rides.ride_distance.
        Matches init_postgres.sql schema exactly.
        """
        try:
            # Try Redis cache first (async)
            cached = await redis_get(f"ride_distance:{ride_id}")
            if cached:
                logger.debug(f"✅ Ride distance from Redis cache: {ride_id}")
                return float(cached)
            
            # Import to avoid circular imports with database module
            from app.core.postgres_db import get_postgres_db
            from app.core.database import init_pg_db
            from sqlalchemy import text

            # Connect table postgresql database
            async for db in init_pg_db():
                result = await db.execute(
                    text("SELECT distance_km FROM analytics.trip WHERE ride_id = :ride_id"),
                    {"ride_id": ride_id}
                )
                row = result.fetchone()
                distance = float(row[0]) if row and row[0] is not None else 0.0

                if distance > 0:
                    await redis_set(f"ride_distance:{ride_id}", str(distance), expire=3600)  # Cache for 1 hour
                
                logger.debug(f"✅ Ride distance from database: {ride_id} = {distance} km")
                return distance
            
        except Exception as e:
            logger.error(f"❌ Error fetching ride distance for {ride_id}: {e}")
            return 0.0

    async def _calculate_customer_arrival_status(self, 
                                                 ctat_minutes: float, 
                                                 ride_id: Optional[str] = None,
                                                 distance_km: Optional[float] = None
                                                 ) -> str:
        """
        FIX: ride_id is optional. If provided, fetch distance from analytics.trip (SQL database).
        If not, use distance_km directly (for new ride predictions).
        """
        try:
            # Validate and convert CTAT to float
            ctat = float(ctat_minutes)

            # Fetch ride distance from database (with Redis caching)
            if ride_id:
                resolved_distance = await self._get_ride_distance(ride_id)
            elif distance_km is not None:
                resolved_distance = float(distance_km)
            else:
                resolved_distance = 0.0

            # If no valid distance, return unknown status
            if resolved_distance <= 0:
                logger.warning("⚠️ No valid distance — returning 'unknown' status.")
                return "unknown"
            
            # Status based on CTAT prediction thresholds
            if ctat < 5: 
                return "arriving_soon"
            elif ctat < 15:
                return "on_the_way"
            elif ctat < 30:
                return "near_dropoff"
            else:
                return "late_arrival"
        
        except ValueError as e:
            logger.error(f"❌ Invalid CTAT value: {ctat_minutes} - {e}")
            return "unknown"
        except Exception as e:
            logger.error(f"❌ Error calculating customer arrival status for ride {ride_id}: {e}")
            return "unknown"