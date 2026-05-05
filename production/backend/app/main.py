from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import logging
import time
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
from app.api.routes import llm

# Prometheus metrics
from app.core.prometheus_metrics import REQUEST_COUNT, REQUEST_LATENCY, ACTIVE_RIDES, PREDICTION_TIME, REGISTRY
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global service references
ml_predictor = None
vehicle_recommender = None
surge_recommender = None
churn_recommender = None
matching_recommender = None

# Middleware to collect metrics
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        latency = time.time() - start_time
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(latency)
        return response

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: Dict, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ml_predictor, vehicle_recommender, surge_recommender, churn_recommender, matching_recommender
    logger.info("Initializing database and services...")
    
    # Load ML models
    ml_predictor = MLPredictor()
    await ml_predictor.load_models()   # note: method is load_models, not load_model
    
    # Initialize Redis client
    redis_client = await get_redis()
    vehicle_recommender = VehicleRecommender(redis_client)
    surge_recommender = SurgeRecommender(redis_client)
    churn_recommender = ChurnRecommender()
    matching_recommender = MatchingRecommender(redis_client)
    
    # Initialize database tables
    await init_db()
    
    logger.info("Initialization complete.")
    yield
    logger.info("Shutting down services...")

# Create FastAPI app
app = FastAPI(title="Taxi Trip API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Prometheus metrics middleware
app.add_middleware(MetricsMiddleware)

# Include routers
app.include_router(prediction.router, prefix="/api/predict", tags=["predictions"])
app.include_router(ride.router, prefix="/api/rides", tags=["rides"])
app.include_router(driver.router, prefix="/api/drivers", tags=["drivers"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(recommendations.router, prefix="/api/recommend", tags=["recommendations"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])

# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "ml_loaded": ml_predictor is not None}

# WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "driver_location":
                redis = await get_redis()
                await redis.set(f"driver:loc:{user_id}", f"{data['lat']},{data['lng']}", ex=15)
                # Notify nearby riders (simplified – all riders)
                for conn_id, conn in manager.active_connections.items():
                    if conn_id.startswith("rider_"):
                        await manager.send_personal_message({
                            "type": "driver_location_update",
                            "driver_id": user_id,
                            "lat": data["lat"],
                            "lng": data["lng"]
                        }, conn_id)
            elif data.get("type") == "ride_status":
                rider_id = data.get("rider_id")
                if rider_id:
                    await manager.send_personal_message({
                        "type": "ride_status",
                        "status": data['status'],
                        "ride_id": data['ride_id']
                    }, rider_id)
    except WebSocketDisconnect:
        manager.disconnect(user_id)