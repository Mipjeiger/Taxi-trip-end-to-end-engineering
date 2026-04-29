from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Dict

from app.api.routes import prediction, ride, driver, analytics, recommendations
from app.core.config import settings
from app.core.database import init_db
from app.services.ml_predictor import MLPredictor
from app.services.vehicle_recommender import VehicleRecommender
from app.services.surge_recommender import SurgeRecommender
from app.services.churn_recommender import ChurnRecommender
from app.services.matching_recommender import MatchingRecommender
from app.core.redis_client import get_redis

# Create logging configuration
logger = logging.getLogger(__name__)

# Global reference for services
ml_predictor = None
vehicle_recommender = None
surge_recommender = None
churn_recommender = None
matching_recommender = None

# Websocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)


# usage of async context manager to initialize services and database
manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ml_predictor, vehicle_recommender, surge_recommender, churn_recommender, matching_recommender
    logger.info("Initializing database and services...")
    ml_predictor = MLPredictor()
    await ml_predictor.load_model()

    # Initialize services that depend on the ML predictor
    redis_client = await get_redis()
    vehicle_recommender = VehicleRecommender(redis_client)
    surge_recommender = SurgeRecommender(redis_client)
    churn_recommender = ChurnRecommender()
    matching_recommender = MatchingRecommender(redis_client)

    await init_db()
    logger.info("Initialization complete.")
    yield # Finish initialization before handling requests
    logger.info("Shutting down services...")

# Create FastAPI app with lifespan for initialization
app = FastAPI(title="Taxi trip API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(prediction.router, prefix="/api/predict", tags=["predictions"])
app.include_router(ride.router, prefix="/api/rides", tags=["rides"])
app.include_router(driver.router, prefix="/api/drivers", tags=["drivers"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(recommendations.router, prefix="/api/recommend", tags=["recommendations"])

# Websocket endpoint for real-time connections
@app.get("/health")
async def health():
    return {"status": "ok", "ml_loader": ml_predictor is not None}

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Broadcast driver location to relevant riders
            if data.get("type") == "driver_location":
                # Update driver position in redis
                redis = await get_redis()
                await redis.set(f"driver:loc:{user_id}", f"{data['lat']},{data['lng']}", ex=15)

                # Notify nearby riders
                for conn_id, conn in manager.active_connections.items():
                    if conn_id.startswith("rider_"):
                        await manager.send_personal_message({
                            "type": "driver_location_update",
                            "driver_id": user_id,
                            "lat": data["lat"],
                            "lng": data["lng"]
                        }, conn_id)
            elif data.get("type") == "ride_status":
                # Forward to specific driver/rider
                rider_id = data.get("rider_id")
                if rider_id:
                    await manager.send_personal_message({
                        "type": "ride_status",
                        "status": data['status'],
                        "ride_id": data['ride_id']
                    }, rider_id)

    except WebSocketDisconnect:
        manager.disconnect(user_id)