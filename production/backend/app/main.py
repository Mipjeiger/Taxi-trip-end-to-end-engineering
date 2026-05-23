from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import logging
import time
import datetime
from typing import Dict

from app.api.routes import prediction, ride, driver, analytics, recommendations, llm
from app.core.config import settings
from app.core.database import init_db
from app.services.ml_predictor import MLPredictor
from app.services.vehicle_recommender import VehicleRecommender
from app.services.surge_recommender import SurgeRecommender
from app.services.churn_recommender import ChurnRecommender
from app.services.matching_recommender import MatchingRecommender
from app.api.dependencies import (
    set_ml_predictor, set_vehicle_recommender, set_surge_recommender,
    set_churn_recommender, set_matching_recommender
)
from app.core.redis_client import get_redis, close_redis
from app.startup import initialize_mlflow
from app.services.kafka_producer import kafka_producer

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
redis_client = None

# Middleware to collect metrics
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        try:
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
        except Exception as e:
            logger.error(f"Middleware error: {e}")
            raise

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        try:
            await websocket.accept()
            self.active_connections[user_id] = websocket
            logger.info(f"✅ WebSocket connected: {user_id}")
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"❌ WebSocket disconnected: {user_id}")

    async def send_personal_message(self, message: Dict, user_id: str):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")
                self.disconnect(user_id)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management - startup and shutdown"""
    global ml_predictor, vehicle_recommender, surge_recommender, churn_recommender, matching_recommender, redis_client, kafka_producer
    
    # ========== STARTUP ==========
    logger.info("=" * 70)
    logger.info("🚀 STARTUP: Initializing application services...")
    logger.info("=" * 70)
    
    try:
        # Step 1: Initialize database
        logger.info("[1/6] Initializing database...")
        await init_db()
        logger.info("✅ Database initialized successfully")

        # Step 2: Initialize Redis
        logger.info("[2/6] Initializing Redis...")
        redis_client = await get_redis()
        logger.info("✅ Redis initialized successfully")

        # Step 3: Initialize Kafka producer
        logger.info("[3/6] Initializing Kafka producer...")
        try:
            kafka_producer.connect()
            kafka_producer._create_topics() # Ensure topics is created or exist
            logger.info("✅ Kafka producer initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Kafka producer initialization failed (non-critical): {e}")

        # Step 4: Initialize MLflow (non-blocking)
        logger.info("[4/6] Initializing MLflow...")
        try:
            initialize_mlflow()
            logger.info("✅ MLflow initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ MLflow initialization failed (non-critical): {e}")

        # Step 5: Load ML models
        logger.info("[5/6] Loading ML models...")
        try:
            ml_predictor = MLPredictor()
            await ml_predictor.load_models()
            set_ml_predictor(ml_predictor)
            logger.info("✅ ML models loaded successfully")
        except Exception as e:
            logger.error(f"❌ ML model loading failed: {e}")
            ml_predictor = None
            raise

        # Step 6: Initialize recommender services
        logger.info("[6/6] Initializing recommender services...")
        try:
            vehicle_recommender = VehicleRecommender(redis_client)
            set_vehicle_recommender(vehicle_recommender)
            logger.info("  ✅ Vehicle recommender initialized")
            
            surge_recommender = SurgeRecommender(redis_client)
            set_surge_recommender(surge_recommender)
            logger.info("  ✅ Surge recommender initialized")
            
            churn_recommender = ChurnRecommender()
            set_churn_recommender(churn_recommender)
            logger.info("  ✅ Churn recommender initialized")
            
            matching_recommender = MatchingRecommender(redis_client)
            set_matching_recommender(matching_recommender)
            logger.info("  ✅ Matching recommender initialized")
        except Exception as e:
            logger.error(f"❌ Recommender initialization failed: {e}")
            raise

        # Step 7: Verify all services
        logger.info("[7/7] Verifying all services...")
        services_status = {
            "Database": "✅" if init_db else "❌",
            "Redis": "✅" if redis_client else "❌",
            "Kafka": "✅" if kafka_producer else "❌",
            "MLflow": "✅" if initialize_mlflow else "❌",
            "ML Models": "✅" if ml_predictor else "❌",
            "Vehicle Recommender": "✅" if vehicle_recommender else "❌",
            "Surge Recommender": "✅" if surge_recommender else "❌",
            "Churn Recommender": "✅" if churn_recommender else "❌",
            "Matching Recommender": "✅" if matching_recommender else "❌",
        }
        
        for service, status in services_status.items():
            logger.info(f"  {status} {service}")

        logger.info("=" * 70)
        logger.info("✅ STARTUP COMPLETE - Application ready!")
        logger.info("=" * 70)

    except Exception as e:
        logger.error("=" * 70)
        logger.error(f"❌ STARTUP FAILED: {str(e)}")
        logger.error("=" * 70)
        raise

    # ========== APP RUNS HERE ==========
    yield

    # ========== SHUTDOWN ==========
    logger.info("=" * 70)
    logger.info("🛑 SHUTDOWN: Cleaning up services...")
    logger.info("=" * 70)
    
    try:
        # Close Redis connection
        logger.info("Closing Redis connection...")
        await close_redis()
        logger.info("✅ Redis closed successfully")

        # Close Kafka producer
        try:
            kafka_producer.close()
            logger.info("✅ Kafka producer closed successfully")
        except Exception as e:
            logger.error(f"❌ Error closing Kafka producer: {e}")

        # Cleanup WebSocket connections
        logger.info(f"Closing {len(manager.active_connections)} WebSocket connections...")
        for user_id in list(manager.active_connections.keys()):
            manager.disconnect(user_id)
        logger.info("✅ WebSocket connections closed")

        logger.info("=" * 70)
        logger.info("✅ SHUTDOWN COMPLETE")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


# Create FastAPI app with lifespan
app = FastAPI(
    title="Taxi Trip API",
    description="Real-time ride prediction and optimization",
    version="1.0.0",
    lifespan=lifespan
)

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
logger.info("Registering API routes...")
app.include_router(prediction.router, prefix="/api/predict", tags=["predictions"])
app.include_router(ride.router, prefix="/api/rides", tags=["rides"])
app.include_router(driver.router, prefix="/api/drivers", tags=["drivers"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(recommendations.router, prefix="/api/recommend", tags=["recommendations"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
logger.info("✅ All routes registered successfully")

# ========== ENDPOINTS ==========

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "services": {
            "ml_models": ml_predictor is not None,
            "redis": redis_client is not None,
            "database": True,
            "websocket_connections": len(manager.active_connections)
        }
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time driver/rider updates"""
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "driver_location":
                # Store driver location in Redis
                await redis_client.set(
                    f"driver:loc:{user_id}",
                    f"{data['lat']},{data['lng']}",
                    ex=15
                )
                logger.debug(f"Driver location updated: {user_id}")
                
                # Send to Kafka for data events
                event = {
                    "type": "driver_location",
                    "driver_id": user_id,
                    "lat": data["lat"],
                    "lng": data["lng"],
                    "timestamp": datetime.datetime.now().isoformat()

                }
                await kafka_producer.send_event("driver-events", event)

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
                # Send ride status to kafka
                event = {
                    "type": "ride_status",
                    "user_id": user_id,
                    "status": data["status"],
                    "timestamp": datetime.datetime.now().isoformat()
                }
                await kafka_producer.send_event("ride-events", event)

                # Notify driver
                rider_id = data.get("rider_id")
                if rider_id:
                    await manager.send_personal_message({
                        "type": "ride_status",
                        "status": data.get('status'),
                        "ride_id": data.get('ride_id')
                    }, user_id)
                
    except WebSocketDisconnect:
        manager.disconnect(user_id)

# Optional: Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "🚕 Taxi Trip Prediction API",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }