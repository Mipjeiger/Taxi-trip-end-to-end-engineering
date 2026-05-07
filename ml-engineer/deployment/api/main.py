import tensorflow as tf
import pickle
import numpy as np
import time
import logging
import os
import joblib
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Literal, Optional
from tensorflow.keras.models import load_model

MODEL_DIR = Path(__file__).parent.parent.parent / "models"
MODEL_DIR_2 = Path(__file__).parent.parent.parent / "models_2"
MODEL_NAME = Literal['Linear Regression', 'Decision Tree', 'XGBoost', 'Neural Network']

app = FastAPI(title="Ride Prediction API", version="1.0")

# Define logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ride_api")

# Load artefacts
scaler = joblib.load(MODEL_DIR_2 / ["scaler_minmax.pkl", "scaler_ultra.pkl"][0])  # FIX 0: was scaler.pkl, now we have two scalers for price and time
feature_list   = joblib.load(MODEL_DIR_2 / ["features_new.pkl", "features_ultra.pkl", "features.pkl"][0])
feature_list_ultra = joblib.load(MODEL_DIR_2 / "features_ultra.pkl")
le_pickup      = joblib.load(MODEL_DIR_2 / "le_pickup.pkl")
le_drop        = joblib.load(MODEL_DIR_2 / "le_drop.pkl")

# Engineer Models
model_keras_price = load_model(MODEL_DIR_2 / "model_price_improved.keras")
model_keras_time  = load_model(MODEL_DIR_2 / "model_time_improved.keras")
model_price_ml = joblib.load(MODEL_DIR_2 / "best_models_ultra_ctat.pkl")
model_trip_ml  = joblib.load(MODEL_DIR_2 / "best_models_ultra_vtat.pkl")

# Schema
class RideRequest(BaseModel):           # FIX 1: was __BaseModel__
    pickup: str
    drop: str
    distance: float
    hour: int
    day_of_week: int
    driver_rating: float
    customer_rating: float
    route_avg_ctat: float
    route_avg_price: float
    route_avg_distance: float
    route_count: int
    model: MODEL_NAME = "XGBoost"

class PredictionResponse(BaseModel):
    request_id: str
    model: str
    prediction: float
    unit: str
    latency_ms: float
    error: Optional[str] = None

# Feature Engineering - Feature builder
def build_features(data: RideRequest) -> np.ndarray:
    try:
        pickup_encoded = le_pickup.transform([data.pickup])[0]
        drop_encoded   = le_drop.transform([data.drop])[0]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    h, dow = data.hour, data.day_of_week
    d      = data.distance

    vec = [
        pickup_encoded,                          # Pickup Encoded
        drop_encoded,                            # Drop Encoded
        d,                                       # FIX 2: distance was missing
        h,                                       # hour
        dow,                                     # day_of_week
        data.driver_rating,                      # Driver Ratings
        data.customer_rating,                    # Customer Rating
        np.log1p(d),                             # log_distance
        d / (h + 1),                             # distance_per_hour
        int(7 <= h <= 9 or 17 <= h <= 19),       # is_peak_hour
        int(dow >= 5),                           # FIX 3: is_weekend was missing
        int(h >= 22 or h < 5),                   # is_night
        np.sin(2 * np.pi * h / 24),              # hour_sin
        np.cos(2 * np.pi * h / 24),              # hour_cos
        np.sin(2 * np.pi * dow / 7),             # FIX 4: day_sin was missing
        np.cos(2 * np.pi * dow / 7),             # day_cos
        data.driver_rating - data.customer_rating,       # rating_diff
        data.driver_rating * data.customer_rating,       # rating_product
        (data.driver_rating + data.customer_rating) / 2, # avg_rating
        int(data.driver_rating < 3.5),           # low_driver_rating
        int(data.customer_rating < 3.5),         # low_customer_rating
        data.route_avg_ctat,                     # route_avg_ctat
        data.route_avg_price,                    # route_avg_price
        data.route_avg_distance,                 # route_avg_distance
        data.route_count,                        # route_count
    ]
    return np.array(vec, dtype=np.float32).reshape(1, -1)

# Predict — FIX 5: NN uses scaled input, ML uses raw (was swapped)
def predict_core(ml_models_dict, nn_model, data: RideRequest):
    X_raw = build_features(data)
    if data.model == "Neural Network":
        X_scaled = scaler.transform(X_raw)       # NN needs scaling
        return float(nn_model.predict(X_scaled)[0][0])
    else:
        ml_model = ml_models_dict[data.model]    # ML uses raw features
        if ml_model is None:
            raise HTTPException(status_code=400, detail=f"Model '{data.model}' not found.")
        pred = ml_model.predict(X_raw)[0]

    return float(pred)

# Generic POST Handler
def handle_prediction(req: RideRequest, ml_models, nn_model, unit: str):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        result = predict_core(ml_models, nn_model, req)
        latency = (time.time() - start_time) * 1000  # ms
        logger.info(f"Request {request_id} | Model: {req.model} | latency: {latency:.2f}ms")

        return PredictionResponse(
            request_id=request_id,
            model=req.model,
            prediction=round(result, 2),
            unit=unit,
            latency_ms=round(latency, 2)
        )
    
    except Exception as e:
        logger.error(f"Request {request_id} | Model: {req.model} | Error: {str(e)}")
        return PredictionResponse(
            request_id=request_id,
            model=req.model,
            prediction=0.0,
            unit=unit,
            latency_ms=0.0,
            error=str(e)
        )
        
# ============================================================
# ROUTES
# ============================================================

# GET endpoints
@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/features")
def get_features():
    return {"count": len(feature_list), "features": feature_list}

@app.get("/features_ultra")
def get_features_ultra():
    return {"count": len(feature_list_ultra), "features": feature_list_ultra}

@app.get("/models")
def get_models():
    return {
        "price": list(model_price_ml.keys()) + ["Neural Network"],
        "trip":  list(model_trip_ml.keys())  + ["Neural Network"],
    }

@app.get("/locations")
def get_locations():
    return {
        "pickup": le_pickup.classes_.tolist(),
        "drop":   le_drop.classes_.tolist(),
    }

# POST endpoints — FIX 6: each endpoint uses its own correct models/nn
@app.post("/predict/price")
def predict_price(request: RideRequest):
    result = predict_core(ml_models_dict=model_price_ml, nn_model=model_keras_price, data=request)
    return {"model": request.model, "price_IDR": round(result, 2)}

@app.post("/predict/trip")
def predict_trip(request: RideRequest):
    result = predict_core(ml_models_dict=model_trip_ml, nn_model=model_keras_time, data=request)
    return {"model": request.model, "duration_minutes": round(result, 2)}

@app.post("/predict/both")
def predict_both(request: RideRequest):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        price = predict_core(ml_models_dict=model_price_ml, nn_model=model_keras_price, data=request)
        trip = predict_core(ml_models_dict=model_trip_ml, nn_model=model_keras_time, data=request)

        latency = (time.time() - start_time) * 1000  # ms

        return {
            "request_id": request_id,
            "model": request.model,
            "price_IDR": round(price, 2),
            "duration_minutes": round(trip, 2),
            "latency_ms": round(latency, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Prediction core based on features in features_ultra
@app.post("/predict/ultra")
def predict_ultra(request: RideRequest):
    result = predict_core(ml_models_dict=model_price_ml, nn_model=model_keras_price, data=request)
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8020, reload=True)