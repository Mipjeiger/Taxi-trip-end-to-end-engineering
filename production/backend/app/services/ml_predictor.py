import pandas as pd
import numpy as np
import pickle
from typing import Dict, Optional, Union
from pathlib import Path
from datetime import datetime, timedelta
from app.core.config import DATABASE_FEATURES_PATH
from app.core.redis_client import redis_get, redis_set
from app.core.postgres_db import get_postgres_db
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
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
        use_fallback: bool = False
    ) -> Dict:
        """ 
        Predict ride metrics (CTAT, VTAT, price, completion time).
        Returns:
            Dict with predictions including estimated_completed_at
        """
        if not self.is_loaded:
            raise RuntimeError("Models not loaded. Call load_models() first.")
        
        if booking_datetime is None:
            booking_datetime = datetime.now()

        try:
            # Pre-compute time-based features
            is_peak_hour = 1 if (7 <= hour <= 9) or (17 <= hour <= 19) else 0
            is_night = 1 if hour >= 22 or hour < 5 else 0

            # Extract features - THIS RETURNS A DATAFRAME
            features_df = await self._extract_features(
                pickup=pickup, 
                drop=drop, 
                vehicle_type=vehicle_type, 
                hour=hour, 
                day_of_week=day_of_week, 
                distance_km=distance_km
            )
            
            # Predict CTAT and VTAT
            try:
                ctat_pred = await self._predict_ctat(features_df, use_fallback)
                vtat_pred = await self._predict_vtat(features_df, use_fallback)
                
                logger.info(f"📊 Model predictions - CTAT: {ctat_pred:.1f}min, VTAT: {vtat_pred:.1f}min")
            
            except Exception as e:
                logger.error(f"❌ ML model prediction failed: {e}")
                
                if 'route_ctat_mean' in features_df.columns and 'route_vtat_mean' in features_df.columns:
                    ctat_pred = float(features_df['route_ctat_mean'].iloc[0])
                    vtat_pred = float(features_df['route_vtat_mean'].iloc[0])
                    
                    logger.info(f"ℹ️ Using route averages: CTAT: {ctat_pred:.1f}min, VTAT: {vtat_pred:.1f}min")
                else:
                    raise RuntimeError("❌ ML model prediction failed and no fallback features available.")
        
            total_time = ctat_pred + vtat_pred

            # Calculate price
            try:
                estimated_price = await self._calculate_price(
                    distance_km=distance_km,
                    time_min=total_time,
                    vehicle_type=vehicle_type,
                    is_peak_hour=is_peak_hour,
                    is_night=is_night,
                    demand_pressure=demand_pressure,
                    rating_avg=rating_avg
                )
            except Exception as e:
                raise RuntimeError(f"❌ Price calculation failed: {e}")

            # Predict timestamps
            completed_at = booking_datetime + timedelta(minutes=ctat_pred)
            vehicle_arrival_at = booking_datetime + timedelta(minutes=vtat_pred)
            
            # Predict vehicle and customer arrival statuses
            vehicle_arrival_status = await self._calculate_vehicle_arrival_status(vtat_pred)
            customer_arrival_status = await self._calculate_customer_arrival_status(ctat_pred, distance_km=distance_km)
            
            # Return prediction dictionary
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
            logger.error(f"❌ Error during prediction: {str(e)}", exc_info=True)
            raise RuntimeError(f"❌ Error in predict_ride_metrics: {e}")

    async def _extract_features(
        self,
        pickup: str,
        drop: str,
        vehicle_type: str,
        hour: int,
        day_of_week: int,
        distance_km: float
    ) -> pd.DataFrame:
        """
        Extract features matching training pipeline by ingesting data from parquet file.
        """
        try:
            # Load the parquet file
            df = pd.read_parquet(DATABASE_FEATURES_PATH)
            logger.info(f"📊 Loaded features parquet: {DATABASE_FEATURES_PATH} with {len(df)} rows and columns: {df.columns.tolist()[:5]}...")
            
            # ============================================================
            # Vehicle Type Mapping & Encoding
            # ============================================================
            # Map parquet vehicle types to database vehicle types
            VEHICLE_TYPE_MAPPING = {
                'Auto': 'Brio',
                'Car': 'Go Sedan',
                'Go Sedan': 'Go Sedan',
                'Motorcycle': 'Brio',
                'Premier Sedan': 'Premier Sedan',
                'eBike': 'Brio',
                'Uber XL': 'Innova',
            }
            
            # Database vehicle type encoding
            VEHICLE_TYPE_ENCODING = {
                'Alphard': 0,
                'HRV': 1,
                'Go Sedan': 2,
                'Innova': 3,
                'Premier Sedan': 4,
                'Brio': 5,
                'Terios': 6,
            }
            
            # Map the input vehicle_type (from parquet) to database vehicle type
            mapped_vehicle_type = VEHICLE_TYPE_MAPPING.get(vehicle_type, 'Go Sedan')
            vehicle_encoded = VEHICLE_TYPE_ENCODING.get(mapped_vehicle_type, 2)
            
            logger.info(f"📊 Vehicle type mapping: {vehicle_type} → {mapped_vehicle_type} (encoded: {vehicle_encoded})")
            
            # Try to find matching route in parquet
            route_features = {}
            for col in df.columns:
                if col in self.features:
                    route_features[col] = float(df[col].mean())

            logger.info(f"✅ Using averaged features from parquet (mean of {len(df)} rows)")

            # ============================================================
            # Build features dictionary
            # ============================================================
            features = {}
            
            # 1. Copy all route features from parquet
            for key, value in route_features.items():
                features[key] = value

            # 2. Override with dynamic values
            features['hour'] = hour
            features['day_of_week'] = day_of_week
            features['distance_km'] = distance_km
            features['log_distance_v2'] = np.log(distance_km + 1)
            features['dist_bin_ctat'] = min(distance_km / 10, 5)
            features['dist_bin_vtat'] = min(distance_km / 10, 5)

            # 3. Time-based features
            features['is_peak_hour'] = 1 if (7 <= hour <= 9) or (17 <= hour <= 19) else 0
            features['is_weekend'] = 1 if day_of_week >= 5 else 0

            # 4. Cylical encoding
            features['hour_sin'] = np.sin(2 * np.pi * hour / 24)
            features['hour_cos'] = np.cos(2 * np.pi * hour / 24)

            # 5. Traffic score based on peak hour
            features['traffic_score'] = 1 + features['is_peak_hour']

            # 6. Price bucket (based on distance)
            if distance_km < 5:
                features['price_bucket_ctat'] = 0
                features['price_bucket_vtat'] = 0
            elif distance_km < 15:
                features['price_bucket_ctat'] = 1
                features['price_bucket_vtat'] = 1
            else:
                features['price_bucket_ctat'] = 2
                features['price_bucket_vtat'] = 2

            # 7. Rating bucket
            features['rating_bucket_ctat'] = 0
            features['rating_bucket_vtat'] = 0

            # 8. Price per km - Adjust price per km amount of 3000 IDR/km for fallback
            features['price_per_km'] = 3000
            features['Booking Value'] = distance_km * 3000

            # 9. Driver and Customer Ratings
            features['Driver Ratings'] = 4.5
            features['Customer Rating'] = 4.5
            features['rating_sum'] = 9.0

            # 10. Estimated times (use route averages or defaults)
            features['estimated_pickup_time_minute'] = features.get('route_vtat_mean', 5.0)
            features['estimated_drop_time_minute'] = features.get('route_ctat_mean', 15.0)

            # 11. Vehicle type encoding (add to features)
            features['Vehicle Type Encoded'] = vehicle_encoded

            # 12. Route cluster (hash of pickup/dropoff coordinates)
            features['route_cluster'] = abs(hash(f"{pickup}_{drop}")) % 100 

            # 13. Pickup and Drop Encodings
            features['Pickup Encoded'] = abs(hash(pickup)) % 1000
            features['Drop Encoded'] = abs(hash(drop)) % 1000

            # 14. Route hour features
            features['route_hour_ctat'] = features.get('route_ctat_mean', 15.0) * (1 + 0.1 + features['is_peak_hour'])
            features['route_hour_vtat'] = features.get('route_vtat_mean', 5.0) * (1 + 0.1 + features['is_peak_hour'])

            # 15. Hourly averages
            features['hour_avg_ctat'] = features.get('hour_avg_ctat', 15.0)
            features['hour_avg_vtat'] = features.get('hour_avg_vtat', 5.0)
            features['hour_demand'] = features.get('hour_demand', 10.0)

            # 16. Day of week averages
            features['dow_avg_ctat'] = features.get('dow_avg_ctat', 15.0)
            features['dow_avg_vtat'] = features.get('dow_avg_vtat', 5.0)
            
            # 17. Route counts
            features['route_count'] = features.get('route_count', 1)

            # ============================================================
            # Create Dataframe with all features
            # ============================================================

            features_df = pd.DataFrame([features])

            # Ensure all features from training exist
            if self.features:
                for col in self.features:
                    if col not in features_df.columns:
                        features_df[col] = 0  # Fill missing features with default value
                        logger.debug(f"⚠️ Missing feature '{col}' added with default value 0.0")

                return features_df[self.features] # Return only the features used in training, in correct order
            
            return features_df
        
        except Exception as e:
            logger.error(f"❌ Error extracting features: {e}", exc_info=True)

            # Return default features using known columns
            default_features = {
                'route_ctat_mean': 15.0,
                'route_ctat_median': 15.0,
                'route_ctat_std': 5.0,
                'route_vtat_mean': 5.0,
                'route_vtat_median': 5.0,
                'route_count': 1,
                'hour_avg_ctat': 15.0,
                'hour_avg_vtat': 5.0,
                'hour_demand': 100,
                'dow_avg_ctat': 15.0,
                'dow_avg_vtat': 5.0,
                'route_hour_ctat': 15.0,
                'route_hour_vtat': 5.0,
                'Ride Distance': distance_km,
                'log_distance_v2': np.log(distance_km + 1),
                'dist_bin_ctat': min(distance_km / 10, 5),
                'dist_bin_vtat': min(distance_km / 10, 5),
                'Driver Ratings': 4.5,
                'Customer Rating': 4.5,
                'rating_sum': 9.0,
                'rating_bucket_ctat': 0,
                'rating_bucket_vtat': 0,
                'Booking Value': distance_km * 3000,
                'price_per_km': 3000,
                'price_bucket_ctat': 0,
                'price_bucket_vtat': 0,
                'hour': hour,
                'day_of_week': day_of_week,
                'hour_sin': np.sin(2 * np.pi * hour / 24),
                'hour_cos': np.cos(2 * np.pi * hour / 24),
                'is_peak_hour': 1 if (7 <= hour <= 9) or (17 <= hour <= 19) else 0,
                'is_weekend': 1 if day_of_week >= 5 else 0,
                'traffic_score': 1 + (1 if (7 <= hour <= 9) or (17 <= hour <= 19) else 0),
                'estimated_pickup_time_minute': 5.0,
                'estimated_drop_time_minute': 15.0,
                'Vehicle Type Encoded': 2,
                'route_cluster': abs(hash(f"{pickup}_{drop}")) % 100,
                'Pickup Encoded': abs(hash(pickup)) % 1000,
                'Drop Encoded': abs(hash(drop)) % 1000,
            }

            df = pd.DataFrame([default_features])
            if self.features:
                for col in self.features:
                    if col not in df.columns:
                        df[col] = 0
                return df[self.features]
            
            return df

    async def _predict_ctat(self, features_df: pd.DataFrame, use_fallback: bool = False) -> float:
        """Predict CTAT using primary or fallback model."""
        try:
            if not isinstance(features_df, pd.DataFrame):
                features_df = pd.DataFrame([features_df])
            
            # Ensure features are properly formatted
            if self.features:
                features_df = features_df[self.features]
            
            # Fill any NaN values
            features_df = features_df.fillna(0)
            
            if not use_fallback and 'ctat_primary' in self.models and self.scalers.get('ultra') is not None:
                features_scaled = self.scalers['ultra'].transform(features_df)
                try:
                    ctat = float(self.models['ctat_primary'].predict(features_scaled)[0])
                except TypeError as e:
                    if "force_all_finite" in str(e):
                        ctat = float(self.models['ctat_primary'].predict(features_scaled)[0])
                    else:
                        raise e
                logger.info(f"✅ CTAT prediction from primary model: {ctat:.2f} min")
                
            elif 'ctat_fallback' in self.models and self.scalers.get('minmax') is not None:
                features_scaled = self.scalers['minmax'].transform(features_df)
                ctat = float(self.models['ctat_fallback'].predict(features_scaled, verbose=0)[0])
                logger.info(f"✅ CTAT prediction from fallback model: {ctat:.2f} min")
                
            else:
                logger.warning("⚠️ No CTAT model available, using route average")
                if 'route_ctat_mean' in features_df.columns:
                    ctat = float(features_df['route_ctat_mean'].iloc[0])
                elif 'estimated_drop_time_minute' in features_df.columns:
                    ctat = float(features_df['estimated_drop_time_minute'].iloc[0])
                else:
                    raise RuntimeError("❌ No CTAT model or feature available for prediction.")
                
                logger.info(f"ℹ️ Using fallback CTAT: {ctat:.2f} min")

            return max(ctat, 5.0)  # Ensure minimum CTAT of 5 minutes
        
        except Exception as e:
            logger.error(f"❌ CTAT prediction error: {e}")
            try:
                if 'route_ctat_mean' in features_df.columns:
                    return float(features_df['route_ctat_mean'].iloc[0])
            except:
                return RuntimeError("❌ CTAT prediction failed and no fallback feature available.")

    async def _predict_vtat(self, features_df: pd.DataFrame, use_fallback: bool = False) -> float:
        """Predict VTAT using primary or fallback model."""
        try:
            if not isinstance(features_df, pd.DataFrame):
                features_df = pd.DataFrame([features_df])

            # Ensure features are properly formatted
            if self.features:
                features_df = features_df[self.features]

            # Fill any NaN values
            features_df = features_df.fillna(0)

            if not use_fallback and 'vtat_primary' in self.models and self.scalers.get('ultra') is not None:
                
                # Use ML model are trained
                features_scaled = self.scalers['ultra'].transform(features_df) # Scale features
                try:
                    vtat = float(self.models['vtat_primary'].predict(features_scaled)[0])
                except TypeError as e:
                    if "force_all_finite" in str(e):
                        vtat = float(self.models['vtat_primary'].predict(features_scaled[0]))
                    else:
                        raise e
                logger.info(f"✅ VTAT prediction from primary model: {vtat:.2f} min")
                    
            elif 'vtat_fallback' in self.models and self.scalers.get('minmax') is not None:
                
                # Use fallback model
                features_scaled = self.scalers['minmax'].transform(features_df)
                vtat = float(self.models['vtat_fallback'].predict(features_scaled, verbose=0)[0])
                logger.info(f"✅ VTAT prediction from fallback model: {vtat:.2f} min")
            else:
                logger.warning("⚠️ No VTAT model available for prediction. Returning default VTAT of 5 minutes.")
                # Try to get from features
                if 'route_vtat_mean' in features_df.columns:
                    vtat = float(features_df['route_vtat_mean'].iloc[0])
                elif 'estimated_pickup_time_minute' in features_df.columns:
                    vtat = float(features_df['estimated_pickup_time_minute'].iloc[0])
                else:
                    raise RuntimeError("❌ No VTAT model or feature available for prediction.")

            return max(vtat, 2.0) # Ensure minimum VTAT of 2 minutes
        
        except Exception as e:
            logger.error(f"❌ VTAT prediction error: {e}")
            try:
                if 'route_vtat_mean' in features_df.columns:
                    return float(features_df['route_vtat_mean'].iloc[0])
            except:
                return RuntimeError("❌ VTAT prediction failed and no fallback feature available.")

    async def _calculate_price(
            self, 
            distance_km: float, 
            time_min: float, 
            vehicle_type: str = "HRV",
            is_peak_hour: int = 0,
            is_night: int = 0,
            demand_pressure: float = 1.0,
            rating_avg: float = 4.5
    ) -> float:
        """Calculate price based on real-time factors and historical database averages.
        """
        try:
            # 1. Fetch dynamic base price per km from PostgreSQL database
            dynamic_price_per_km = None
            try:
                from app.core.postgres_db import get_postgres_db
                from sqlalchemy import text

                async for db in get_postgres_db():
                    result = await db.execute(
                        text("""
                            SELECT
                                AVG(estimated_fare)
                            FROM analytics.trip
                            WHERE ride_type = :vehicle_type
                                AND estimated_fare > 0
                                AND estimated_fare IS NOT NULL
                        """),
                        {"vehicle_type": vehicle_type}
                    )
                    row = result.fetchone()

                    if row and row[0] is not None:
                        dynamic_price_per_km = float(row[0])
                        logger.info(f"📊 Computed dynamic base price from DB: {dynamic_price_per_km:.2f} IDR/km for {vehicle_type}")

                        break

            except:
                logger.warning(f"⚠️ Could not compute dynamic price from DB, using fallback for {vehicle_type}: {e}")

            # 3. If DB value exists, use it directly (with minor real-time adjustments)
            if dynamic_price_per_km is not None:
               peak_surge = 1.35 if is_peak_hour else 1.0
               night_surge = 1.25 if is_night else 1.0
               final_price = dynamic_price_per_km * peak_surge * night_surge
            else:

                # 3. Fallback: compute from scratch if DB is unavailable
                vehicle_base_price = {
                "Alphard": 3500, "HRV": 2800, "Go Sedan": 2500,
                "Innova": 3000, "Premier Sedan": 3200, "Brio": 2200, "Terios": 2700
                }
                base_price_per_km = vehicle_base_price.get(vehicle_type, 2800)

                # Time-based surges
                peak_surge = 1.35 if is_peak_hour else 1.0
                night_surge = 1.25 if is_night else 1.0
                
                # Calculate fare
                distance_price = distance_km * base_price_per_km
                time_price = time_min * 150
                base_fare = 15000
                
                final_price = (base_fare + distance_price + time_price) * peak_surge * night_surge

                min_fare = 20000
                max_fare = 800000
                return max(min_fare, min(final_price, max_fare))

        except Exception as e:
            logger.error(f"❌ Price calculation error: {e}")
            return 50000
        
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
                return "arriving_soon"
            elif vtat < 15:
                return "arriving"
            elif vtat < 30:
                return "coming"
            else:
                return "delayed"

        except Exception as e:
            logger.error(f"❌ Error calculating vehicle arrival status: {e}")
            return "coming"
        
    async def predict_completed_at(
            self,
            booking_datetime: datetime,
            ctat_minutes: float,
            booking_status: str = "Completed"
    ) -> Union[datetime, str]:
        """
        Predict for completed_at using CTAT prediction.
        Formula: based on machine learning algorithm prediction
        """

        if booking_status != "Completed":
            return "No Trip"
        try:
            return booking_datetime + timedelta(minutes=float(ctat_minutes))

        except Exception as e:
            logger.error(f"❌ Error predicting completed at: {e}")
            return booking_datetime + timedelta(minutes=20)

    async def predict_vehicle_arrival(
            self,
            booking_datetime: datetime,
            vtat_minutes: float,
            booking_status: str = "Completed"
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

        if booking_status != "Completed":
            return datetime(2026, 1, 1, 0, 0, 0)

        try:
            return booking_datetime + timedelta(minutes=float(vtat_minutes))
        
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
            from sqlalchemy import text

            # Connect table postgresql database
            async for db in get_postgres_db():
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
            
            return 0.0
            
        except Exception as e:
            logger.error(f"❌ Error fetching ride distance for {ride_id}: {e}")
            return 0.0

    async def _calculate_customer_arrival_status(
            self, 
            ctat_minutes: float, 
            ride_id: Optional[str] = None,
            distance_km: Optional[float] = None
    ) -> str:
        """Calculate customer arrival status based on CTAT."""
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
    
        except Exception as e:
            logger.error(f"❌ Error calculating customer arrival status for ride {ride_id}: {e}")
            return "unknown"