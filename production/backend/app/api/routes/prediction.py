import logging
import numpy as np
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from app.services.ml_predictor import MLPredictor
from app.api.dependencies import get_ml_predictor
from app.models.prediction import ( PredictionRequest, RidePredictionResponse, VehicleArrivalStatus, DriverStatus )

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
        # Use current time if not specified
        if request.hour is None:
            request.hour = datetime.now().hour
        if request.day_of_week is None:
            request.day_of_week = datetime.now().weekday()

        booking_datetime = datetime.now()

        # Get ML predictions
        prediction = await ml_predictor.predict_ride_metrics(
            pickup=request.pickup_location,
            drop=request.drop_location,
            vehicle_type=request.vehicle_type,
            hour=request.hour,
            day_of_week=request.day_of_week,
            distance_km=request.distance_km,
            booking_datetime=booking_datetime,
            demand_pressure=request.demand_pressure,
            rating_avg=request.rating_avg
        )

        # Transform to response model
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
        raise HTTPException(status_code=500, detail=f"Route comparison failed: {str(e)}")