from pathlib import Path
from dotenv import load_dotenv
import logging
import os
import mlflow
import json
import threading
from typing import Optional

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
# Kafka Consumer (runs as background task)
# ----------------------------------------------------------------
def _delivery_report(err, msg):
    """Kafka producer delivery report callback"""
    if err:
        logger.error(f"❌ Kafka delivery failed for message {msg.key().decode('utf-8')}: {err}")
    else:
        logger.debug(f"✅ Kafka message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")


def _consume_loop(bootstrap_servers: str, topics: list[str], group_id: str):
    """Blocking consumer loop - runs in a thread via run_in_executor.
    Add business logic inside the for-loop."""
    try:
        from confluent_kafka import Consumer, KafkaException
    except ImportError:
        logger.warning("⚠️ confluent_kafka library is not installed. Kafka consumer will be unavailable.")
        return
    try:
        consumer = Consumer({
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
            "session.timeout.ms": 30000
        })
        consumer.subscribe(topics)
        logger.info(f"🎧 Kafka consumer subscribed to topics: {topics}")
    
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                raise KafkaException(msg.error())
            
            try:
                payload = json.loads(msg.value().decode('utf-8'))
                event_type = payload.get("event_type", "unknown")
                logger.info(f"📨 [{msg.topic()}] event_type={event_type} key={msg.key()}")

                # Route events to handlers
                if msg.topic() == "ride-requests":
                    _handle_ride_request(payload)
                elif msg.topic() == "ride-events":
                    _handle_ride_event(payload)
                elif msg.topic() == "driver-events":
                    _handle_driver_event(payload)
            
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Failed to decode JSON from message on topic {msg.topic()} : {msg.value()}")
            except Exception as e:
                logger.error(f"❌ Error processing message from topic {msg.topic()}: {e}")

    except Exception as e:
        logger.error(f"❌ Kafka consumer error: {e}")
    finally:
        try:
            # Close connection on exit
            consumer.close()
            logger.info("🛑 Kafka consumer closed.")
        except:
            pass

# Create function for handling ride requests
def _handle_ride_request(payload: dict):
    logger.info(f" 🚗 -> ride request: ride_id={payload.get('ride_id')}")
    # TODO: trigger matching, surge check, etc.

def _handle_ride_event(payload: dict):
    logger.info(f" 🚗 -> ride event: ride_id={payload.get('ride_id')} event_type={payload.get('event_type')}")
    # TODO: update ride status in Redis/DB

def _handle_driver_event(payload: dict):
    logger.info(f" 🚗 -> driver event: driver_id={payload.get('driver_id')} event_type={payload.get('event_type')}")
    # TODO: update driver location/availability

# ----------------------------------------------------------------
# Kafka Initialization (called from FastAPI lifespan)
# ----------------------------------------------------------------

_consumer_thread: Optional[threading.Thread] = None

async def initialize_kafka():
    """
    Call this once from FastAPI lifespan startup.
    Initialises the producer singleton and spawns the consumer task.
    """
    global _consumer_thread

    try:
        # 1. init the producer singleton (with existing framework in kafka_producer)
        from app.services.kafka_producer import kafka_producer
        
        # Kafka producer is already initialized
        logger.info("🔌 Kafka producer initialized ready.")

        # Start consumer thread
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        topics = ["driver-events", "ride-events", "ride-requests"]
        group_id = "taxi-trip-backend"

        _consumer_thread = threading.Thread(
            target=_consume_loop, 
            args=(bootstrap_servers, topics, group_id), 
            name="kafka-consumer",
            daemon=True
        )
        _consumer_thread.start()
        logger.info("🚀 Kafka consumer thread started.")

    except Exception as e:
        logger.error(f"❌ Kafka initialization failed: {e}")

async def shutdown_kafka():
    """Shutdown Kafka consumer gracefully on FastAPI shutdown."""
    global _consumer_thread

    try:
        from app.services.kafka_producer import kafka_producer
        kafka_producer.close()  # close producer connection if needed
        logger.info("✅ Kafka producer connection closed.")
    except Exception as e:
        logger.warning(f"⚠️ Error closing Kafka producer: {e}")

    # Consumer thread will exit on its own since it's a daemon thread
    if _consumer_thread and _consumer_thread.is_alive():
        logger.info("🛑 Kafka consumer thread will be stopped on process exit.")
        _consumer_thread.join(timeout=5)

    logger.info("✅ Kafka shutdown complete.")