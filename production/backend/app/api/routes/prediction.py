from app.core.redis_client import redis_set_json
from app.core.redis_client import redis_get_json, get_redis
import logging
import numpy as np
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from app.services.ml_predictor import MLPredictor
from app.api.dependencies import get_ml_predictor
from app.models.prediction import ( PredictionRequest, RidePredictionResponse, VehicleArrivalStatus, DriverStatus )
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/predict_ride", response_model=RidePredictionResponse)
async def predict_ride(request: PredictionRequest, ml_predictor: MLPredictor = Depends(get_ml_predictor)):
    """
    Predict ride metrics including VTAT vehicle arrival timestamp.

    Returns:
    - estimated_vehicle_arrival_at: Timestamp when vehicle arrives at pickup
    - vehicle_arrival_status: Status (arriving_soon/arriving/coming/delayed)
    - Full timing & pricing predictions
    """
    try:
        # Unique cache key for exact paramaters
        prediction_cache_key = f"cache:pred:{request.pickup_location}:{request.drop_location}:{request.vehicle_type}:{request.hour}"

        # 1. Prediction cache check (Target < 2ms response)
        cached_prediction = await redis_get_json(prediction_cache_key)

        if cached_prediction:
            logger.info(f"🎯 Prediction cache hit: {prediction_cache_key}")
            
            return RidePredictionResponse(**cached_prediction)
        
        # 2. Get location encodings safely from RedisService framework
        pickup_encoded = await RedisService.get_location_encoding(request.pickup_location, "pickup")
        drop_encoded = await RedisService.get_location_encoding(request.drop_location, "drop")

        # Fallback default values if encodings are not in Redis cache yet
        if pickup_encoded is None:
            pickup_encoded = 0
        if drop_encoded is None:
            drop_encoded = 0

        # Fetch route features from Redis Hash
        route_features = await RedisService.get_route_features(request.pickup_location, request.drop_location)

        # 3. Model Inference (Pass precomputed features into local model) -  Get ML predictions
        prediction = await ml_predictor.predict_ride_metrics(
            pickup=request.pickup_location,
            drop=request.drop_location,
            vehicle_type=request.vehicle_type,
            hour=request.hour,
            day_of_week=request.day_of_week,
            distance_km=request.distance_km
        )

        # 4. Cache prediction result
        await redis_set_json(prediction_cache_key, prediction, expire=300)

        return RidePredictionResponse(**prediction)
    
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
    
@router.post("/compare_routes")
async def compare_routes(
    pickup_drops: list[tuple[str, str]],
    vehicle_type: str = "HRV",
    ml_predictor: MLPredictor = Depends(get_ml_predictor)
):
    """
    Compare multiple routes to show VTAT differences.
    Useful for route optimization.
    """
    try:
        booking_datetime = datetime.now()
        hour = booking_datetime.hour
        day_of_week = booking_datetime.weekday()

        results = []
        for pickup, drop in pickup_drops:
            prediction = await ml_predictor.predict_ride_metrics(
                pickup=pickup,
                drop=drop,
                vehicle_type=vehicle_type,
                hour=hour,
                day_of_week=day_of_week,
                distance_km=10.0,  # Default distance for comparison
                booking_datetime=booking_datetime,
            )
            results.append({
                "route": f"{pickup} -> {drop}",
                "vtat_minute": prediction.get('estimated_vehicle_arrival_minute'),
                "ctat_minute": prediction.get('estimated_drop_time_minute'),
                "price_idr": prediction.get('estimated_price_idr'),
                "vehicle_status": prediction.get('vehicle_arrival_status')
            })

        # Sort by VTAT (fastest vehicle arrival)
        results.sort(key=lambda x: x['vtat_minute'])

        return {
            "booking_time": booking_datetime.isoformat(),
            "vehicle_type": vehicle_type,
            "routes_sorted_by_vtat": results
        }
    
    except Exception as e:
        logger.error(f"Route comparison error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"❌ Route comparison failed: {str(e)}")