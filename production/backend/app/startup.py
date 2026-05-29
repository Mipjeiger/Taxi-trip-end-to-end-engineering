from pathlib import Path
from dotenv import load_dotenv
import logging
import os
import mlflow
import json
import threading
from typing import Optional

# ----------------------------------------------------------------
# Set up
# ----------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
logging.info(f"✅ Loaded environtment variables from: {ENV_PATH}")

if not ENV_PATH.exists():
    ENV_PATH = BASE_DIR.parent / '.env'
    logging.warning(f"⚠️ .env file not found at {ENV_PATH}, trying fallback location: {ENV_PATH}")

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
            return
        
        model_files = list(models_dir.glob("*.keras")) + list(models_dir.glob("*.pkl"))
        logger.info(f"📂 Found {len(model_files)} model files in {models_dir}")
        
        # Loop through and log each model
        for model_file in model_files:
            logger.info(f"   - {model_file.name}")

        # MLflow initialization
        mlflow_uri = os.getenv("MLFLOW_TRACKING_URI")
        if mlflow_uri:
            mlflow.set_tracking_uri(mlflow_uri)
            logger.info(f"🔗 Connected to MLflow at {mlflow.get_tracking_uri()}")
        else:
            logger.warning("⚠️ MLFLOW_TRACKING_URI is not set. MLflow logging will be unavailable.")
    
    except Exception as e:
        logger.error(f"❌ MLflow initialization failed: {str(e)}")
        raise

# ----------------------------------------------------------------
# Kafka Producer Initialization (singleton)
# ----------------------------------------------------------------
async def initialize_kafka_producer():
    """Initialize kafka producer singleton"""
    try:
        from app.services.kafka_producer import kafka_producer

        kafka_producer.initialize()  # Initialize the producer connection
        logger.info("✅ Kafka producer initialized and ready.")
        logger.info("📒 Topics: ride-requests, ride-events, driver-events, frontend-events")
        return True
    
    except Exception as e:
        logger.warning(f"⚠️ Kafka producer initialization failed: {str(e)}. Kafka producer will be unavailable.")
        return False

# ----------------------------------------------------------------
# Kafka Consumer Thread Management
# ----------------------------------------------------------------

_consumer_thread: Optional[threading.Thread] = None
_consumer_instance = None # Store consumer instance for graceful shutdown

async def initialize_kafka_consumer():
    """
    Initialize kafka consumer in background thread.
    The consumer will run in a separate thread and will be stopped gracefully on shutdown.
    """
    global _consumer_thread, _consumer_instance

    try:
        from app.services.kafka_consumer import EventConsumer
        
        # Get bootstrap servers from env
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        logger.info(f"🔌 Initializing Kafka consumer with bootstrap servers: {bootstrap_servers}")

        # Create the EventConsumer instance
        _consumer_instance = EventConsumer(bootstrap_servers=bootstrap_servers)
        logger.info("✅ Kafka consumer instance created successfully.")

        # Start consumer thread
        _consumer_thread = threading.Thread(
            target=_consumer_instance.start,
            name="kafka-consumer",
            daemon=True
        )
        _consumer_thread.start()
        logger.info("🚀 Kafka consumer thread started.")
        logger.info("🎧 Subscribed to topics: ride-requests, ride-events, driver-events, frontend-events")
        return True

    except Exception as e:
        logger.error(f"❌ Kafka initialization failed: {e}")
        return False

async def shutdown_kafka_consumer():
    """Shutdown Kafka consumer gracefully on FastAPI shutdown."""
    global _consumer_thread, _consumer_instance

    if _consumer_instance:
        try:
            _consumer_instance.stop()
        except Exception as e:
            logger.warning(f"⚠️ Error stopping Kafka consumer: {e}")

    # Consumer thread will exit on its own since it's a daemon thread
    if _consumer_thread and _consumer_thread.is_alive():
        logger.info("🛑 Kafka consumer thread will be stopped on process exit.")
        _consumer_thread.join(timeout=5)
        logger.info("✅ Kafka consumer thread stopped.")

async def shutdown_kafka_producer():
    """Shutdown Kafka producer gracefully on FastAPI shutdown."""
    try:
        from app.services.kafka_producer import kafka_producer
        kafka_producer.close()
        logger.info("✅ Kafka producer shutdown complete.")
    except Exception as e:
        logger.warning(f"⚠️ Error shutting down Kafka producer: {e}")

# ================================================================
# Main Initialization Functions (called from main.py lifespan)
# ================================================================

async def initialize_kafka():
    """Initialize both kafka producer and consumer."""
    logger.info("🔌 Initializing Kafka producer and consumer...")

    producer_ok = await initialize_kafka_producer()
    consumer_ok = await initialize_kafka_consumer()

    if not producer_ok or not consumer_ok:
        logger.warning("⚠️ Kafka initialization had issues. Check logs for details.")
    else:
        logger.info("✅ Kafka producer and consumer initialized successfully.")

async def shutdown_kafka():
    """Shutdown both kafka producer and consumer gracefully."""
    logger.info("🛑 Shutting down Kafka producer and consumer...")

    await shutdown_kafka_consumer()
    await shutdown_kafka_producer()
    logger.info("✅ Kafka shutdown complete.")