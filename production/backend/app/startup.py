from pathlib import Path
from dotenv import load_dotenv
import logging
import os
import mlflow
import asyncio
import json
import time
import threading
from kafka.consumers.events_to_databricks import EventConsumer

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
        producer.produce(
            topic=topic,
            key=key.encode('utf-8'),
            value=json.dumps(payload).encode('utf-8'),
            callback=_delivery_report
        )
        producer.poll(0)  # Trigger delivery report callbacks
    except Exception as e:
        logger.error(f"❌ Kafka produce error on topic '{topic}': {e}")

def _delivery_report(err, msg):
    if err:
        logger.error(f"❌ Kafka delivery failed for message {msg.key().decode('utf-8')}: {err}")
    else:
        logger.debug(f"✅ Kafka message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")


# ----------------------------------------------------------------
# Kafka Consumer (runs as background task)
# ----------------------------------------------------------------
_consumer_task: asyncio.Task | None = None

def _consume_loop(bootstrap_servers: str, topics: list[str], group_id: str):
    """Blocking consumer loop - runs in a thread via run_in_executor.
    Add business logic inside the for-loop."""
    from confluent_kafka import Consumer, KafkaException

    consumer = Consumer({
        "bootstrap.servers": bootstrap_servers,
        "group.id": group_id,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
        "session.timeout.ms": 30000
    })
    consumer.subscribe(topics)
    logger.info(f"🎧 Kafka consumer subscribed to topics: {topics}")
    
    # Logic to consume messages while True
    try:
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

    except asyncio.CancelledError:
        pass
    finally:
        consumer.close()
        logger.info("🛑 Kafka consumer closed.")

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
# Main initializer - called from FastAPI startup event (main.py)
# ----------------------------------------------------------------
_databricks_consumer: EventConsumer | None = None
_consumer_thread: threading.Thread | None = None

async def initialize_kafka():
    """
    Call this once from FastAPI lifespan startup.
    Initialises the producer singleton and spawns the consumer task.
    """
    global _kafka_producer, _consumer_task, _databricks_consumer, _consumer_thread

    # 1. init the producer singleton (with existing framework in kafka_producer)
    from app.services.kafka_producer import kafka_producer
    kafka_producer.initialize() # deffered connection and topic creation

    # 2. Start Databricks consumer in background thread
    _databricks_consumer = EventConsumer()
    _consumer_thread = threading.Thread(
        target=_databricks_consumer.start,
        name="kafka-databricks-consumer",
        daemon=True
    )
    _consumer_thread.start()
    logger.info("✅ Databricks Kafka consumer started in background thread.")

async def shutdown_kafka():
    from app.services.kafka_producer import kafka_producer
    kafka_producer.close()

    if _databricks_consumer:
        _databricks_consumer.stop()
    
    if _consumer_thread:
        _consumer_thread.join(timeout=15)
    logger.info("✅ Databricks Kafka consumer thread stopped.")