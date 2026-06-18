from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import logging
import time
import datetime
import threading
from typing import Dict

from app.api.routes import prediction, ride, driver, analytics, recommendations, llm
from app.core.config import settings
from app.core.database import init_db, init_pg_db
from app.services.ml_predictor import MLPredictor
from app.services.vehicle_recommender import VehicleRecommender
from app.services.surge_recommender import SurgeRecommender
from app.services.churn_recommender import ChurnRecommender
from app.services.matching_recommender import MatchingRecommender
from app.api.dependencies import (
    set_ml_predictor, set_vehicle_recommender, set_surge_recommender,
    set_churn_recommender, set_matching_recommender
)
from app.api.routes import health

# Redis & MLflow imports
from app.core.redis_client import get_redis, close_redis
from app.startup import initialize_mlflow, initialize_kafka, shutdown_kafka

# Kafka producer & consumer
from app.services.kafka_producer import kafka_producer

# Prometheus metrics
from app.core.prometheus_metrics import REQUEST_COUNT, REQUEST_LATENCY, ACTIVE_RIDES, PREDICTION_TIME, REGISTRY
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Evidently AI imports
from app.api.routes import evidently
from app.api.routes.analytics import router as analytics_router

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
    global ml_predictor, vehicle_recommender, surge_recommender, churn_recommender, \
    matching_recommender, redis_client, kafka_producer, _databricks_consumer, _consumer_thread
    
    # ========== STARTUP ==========
    logger.info("=" * 70)
    logger.info("🚀 STARTUP: Initializing application services...")
    logger.info("=" * 70)
    
    try:
        # Step 1: Initialize database
        logger.info("[1/6] Initializing database...")
        await init_db()
        await init_pg_db()
        logger.info(f"✅ Database initialized successfully on Supabase on host: {settings.SUPABASE_HOST}")
        logger.info(f"✅ Database initialized successfully on Docker PostgreSQL on host: {settings.POSTGRES_HOST}")

        # Step 2: Initialize Redis
        logger.info("[2/6] Initializing Redis...")
        redis_client = await get_redis()
        logger.info("✅ Redis initialized successfully")

        # Step 3: Initialize Kafka
        logger.info("[3/6] Initializing Kafka...")
        try:
            await initialize_kafka()
            logger.info("✅ Kafka initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Kafka initialization failed (non-critical): {e}")

        # Step 4: Initialize MLflow (non-blocking)
        logger.info("[4/6] Initializing MLflow...")
        try:
            await initialize_mlflow()
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

        # Step 6: Intialize PostgreSQL connection for analytics
        logger.info("[6/6] Initializing PostgreSQL connection for analytics...")
        try:
            from app.core.postgres_db import postgres_con
            if await postgres_con.verify_connection():
                logger.info("✅ PostgreSQL connection for analytics is healthy")
            else:
                logger.warning("⚠️ PostgreSQL connection for analytics failed health check")
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection initialization failed: {e}")

        # Load recommendation models
        logger.info("Loading recommendation models...")
        try:
            vehicle_recommender = VehicleRecommender(redis_client=redis_client)
            surge_recommender = SurgeRecommender(redis_client=redis_client)
            churn_recommender = ChurnRecommender()
            matching_recommender = MatchingRecommender(redis_client=redis_client)
            
            set_vehicle_recommender(vehicle_recommender)
            set_surge_recommender(surge_recommender)
            set_churn_recommender(churn_recommender)
            set_matching_recommender(matching_recommender)
            
            logger.info("✅ Recommendation models loaded successfully")
        except Exception as e:
            logger.warning(f"⚠️ Recommendation models failed (non-critical): {e}")

        logger.info("=" * 70)
        logger.info("✅ APPLICATION STARTUP COMPLETE")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Critical startup error: {e}", exc_info=True)
        raise

    yield

    # ========== SHUTDOWN ==========
    logger.info("=" * 70)
    logger.info("🛑 SHUTDOWN: Cleaning up resources...")
    logger.info("=" * 70)

    try:
        from app.core.postgres_db import postgres_con
        await postgres_con.close()
        logger.info("✅ PostgreSQL connection closed")
    except Exception as e:
        logger.warning(f"⚠️ PostgreSQL shutdown error: {e}")
    
    try:
        await shutdown_kafka()
        logger.info("✅ Kafka shutdown complete")
    except Exception as e:
        logger.warning(f"⚠️ Kafka shutdown error: {e}")

    try:
        if redis_client:
            await close_redis()
            logger.info("✅ Redis connection closed")
    except Exception as e:
        logger.warning(f"⚠️ Redis shutdown error: {e}")

    logger.info("=" * 70)
    logger.info("✅ APPLICATION SHUTDOWN COMPLETE")
    logger.info("=" * 70)

# Create FastAPI app
app = FastAPI(
    title="Trip Service API",
    description="AI-powered ride-sharing platform with ML predictions",
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

# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Include routers
app.include_router(health.router)
app.include_router(prediction.router, prefix="/api/predictions", tags=["Predictions"])
app.include_router(ride.router, prefix="/api/rides", tags=["Rides"])
app.include_router(driver.router, prefix="/api/drivers", tags=["Drivers"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["Recommendations"])
app.include_router(llm.router, prefix="/api/llm", tags=["LLM"])
app.include_router(evidently.router, prefix="/api/evidently", tags=["Evidently"])

# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "✅ Healthy",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "services": {
            "database": "✅ Connected" if ml_predictor else "⚠️ Initializing",
            "redis": "✅ Connected" if redis_client else "❌ Not connected",
            "ml_models": "✅ Loaded" if ml_predictor else "❌ Not loaded"
        }
    }

# Metrics endpoint (Prometheus)
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)

# WebSocket endpoint for real-time updates
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(user_id: str, websocket: WebSocket):
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            logger.debug(f"Received from {user_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        logger.info(f"Client {user_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for {user_id}: {e}")
        manager.disconnect(user_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)