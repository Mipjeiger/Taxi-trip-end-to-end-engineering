from pathlib import Path
from dotenv import load_dotenv
import logging
import os
import mlflow
import asyncio
import json
import time

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

# ----------------------------------------------------------------
# MLFlow Initialization
# ----------------------------------------------------------------
async def initialize_mlflow():
    """Initialize and log all existing models to MLflow"""
    try:
        models_dir = Path("/app/models")
        if not models_dir.exists():
            logger.warning(f"⚠️ Models directory not found at {models_dir}")
        else:
            model_files = list(models_dir.glob("*.keras")) + list(models_dir.glob("*.pkl"))
            logger.info(f"📂 Found {len(model_files)} model files in {models_dir}")
            
            # Loop through and log each model
            for model_file in model_files:
                logger.info(f"   - {model_file.name}")

        # MLflow init with timeout
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
        logger.info(f"🔗 Connected to MLflow at {mlflow.get_tracking_uri()}")
    
    except Exception as e:
        logger.error(f"❌ MLflow initialization failed: {str(e)}")
        raise

# ----------------------------------------------------------------
# Kafka Producer (module-level sigleton)
# ----------------------------------------------------------------

_kafka_producer = None

def get_kafka_producer():
    """Return the global Confluent Kafka Producer, intialized once."""
    global _kafka_producer
    if _kafka_producer is None:
        raise RuntimeError("Kafka producer is not initialized. Call initialize_kafka_producer() first.")
    return _kafka_producer

def produce_event(topic: str, key: str, payload: dict):
    """Fire-and-forget Kafka Produce. Safe to call from any route.
    Delivery errors are logged but nerver raise to othe caller"""
    try:
        producer = get_kafka_producer()
        