from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.services.matching_recommender import MatchingRecommender
from app.api.dependencies import get_redis_client
import redis.asyncio as redis
from app.services.route_optimizer import RouteOptimizer

router = APIRouter()

class DriverLocationUpdate(BaseModel):
    driver_id: int
    lat: float
    lng: float
    status: str # Online, Offline, on_trip

@router.post("/location")
async def update_driver_location(update: DriverLocationUpdate, 
                                 redis_client: redis.Redis = Depends(get_redis_client)):
    """Store driver real-time location and status in Redis."""
    await redis_client.setex(f"driver:loc:{update.driver_id}", 300, f"{update.lat}, {update.lng}, {update.status.lower()}")
    return {"status": "updated", "driver_id": update.driver_id}

@router.get("/nearby")
async def get_nearby_drivers(lat: float, lng: float, radius_km: float = 2.0, redis_client: redis.Redis = Depends(get_redis_client)):
    """Get nearby drivers within a certain radius."""
   
    nearby_drivers = []
    keys = await redis_client.keys("driver:loc:*")

    for key in keys:
        data = await redis_client.get(key)
        if not data:
            continue
        
        try:
           parts = data.split(",")
           driver_lat = float(parts[0])
           driver_lng = float(parts[1])
           status = parts[2].strip().lower()
        except (ValueError, IndexError):
            continue

        if status != "online":
            continue

        # Correct haversine distance calculation
        distance = RouteOptimizer.haversine(lat, lng, driver_lat, driver_lng)

        if distance <= radius_km:
            driver_id = int(key.decode().split(":")[-1]) if isinstance(key, bytes) else int(key.split(":")[-1])
            nearby_drivers.append({
                "driver_id": driver_id,
                "lat": driver_lat,
                "lng": driver_lng,
                "distance_km": round(distance, 3)
            })

    # Sort by closest distance
    nearby_drivers.sort(key=lambda x: x["distance_km"])
    return {"nearby_drivers": nearby_drivers}