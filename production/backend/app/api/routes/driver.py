from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from app.services.matching_recommender import MatchingRecommender
from app.api.dependencies import get_matching_recommender, get_redis_client
import redis.asyncio as redis

router = APIRouter()

class DriverLocationUpdate(BaseModel):
    driver_id: int
    lat: float
    lng: float
    status: str # Online, Offline, on_trip

@router.post("/location")
async def update_driver_location(update: DriverLocationUpdate, redis_client: redis.Redis = Depends(get_redis_client)):
    """Store driver real-time location and status in Redis."""
    await redis_client.setex(f"driver:loc:{update.driver_id}", 30, f"{update.lat}, {update.lng}, {update.status}")
    return {"status": "updated"}

@router.get("/nearby")
async def get_nearby_drivers(lat: float, lng: float, radius_km: float = 2.0, redis_client: redis.Redis = Depends(get_redis_client)):
    """Get nearby drivers within a certain radius."""
    # This is a simplified example. In production, use geospatial indexing in Redis or a spatial database.
    nearby_drivers = []
    keys = await redis_client.keys("driver:loc:*")
    for key in keys:
        data = await redis_client.get(key)
        if data:
            driver_id = int(key.split(":")[-1])
            driver_lat, driver_lng, status = data.split(", ")
            driver_lat, driver_lng = float(driver_lat), float(driver_lng)
            if status == "online":
                distance = ((driver_lat - lat) ** 2)
                if distance <= (radius_km / 111) ** 2: # Approximate conversion from km to degrees
                    nearby_drivers.append({"driver_id": driver_id, "lat": driver_lat, "lng": driver_lng})
            
    return {"nearby_drivers": nearby_drivers}