import logging
import json
import threading
import time
import os
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR.parent / '.env'
if not ENV_PATH.exists():
    ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

# ================================================================
# Optional Dependencies
# ================================================================

try:
    from confluent_kafka import Consumer, KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("⚠️ confluent_kafka library is not installed. Kafka consumer will be unavailable.")

# ================================================================
# Kafka Event Consumer with Databricks Persistence
# ================================================================

class EventConsumer:
    """
    Kafka consumer: Frontend events -> DuckDB
    Batches events every 100 messages or 30 seconds, whichever comes first.
    """

    TOPICS = ["ride-requests", "ride-events", "driver-events", "frontend-events"]
    BATCH_SIZE = 100
    FLUSH_INTERVAL = 30  # seconds

    def __init__(self, bootstrap_servers: str = None):
        self.bootstrap_servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092") # Use port internal access (in docker .env)
        self.consumer = None
        self._stop_event = threading.Event()
        self._batch: list[dict] = []
        self._last_flush = time.time()
        logger.info(f"📊 EventConsumer initialized with bootstrap_servers: {self.bootstrap_servers}")

    def _connect_kafka(self):
        """Initialize Kafka consumer connection"""
        if not KAFKA_AVAILABLE:
            raise RuntimeError("Kafka consumer cannot be initialized because confluent_kafka is not available.")
        
        try:
            config = {
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": "events-to-duckdb",
                "auto.offset.reset": "earliest",
                "enable.auto.offset.store": False,  
                "enable.auto.commit": False,  # Manual commit after batch is processed
                "session.timeout.ms": 30000,
                "max.poll.interval.ms": 300000,
                "socket.timeout.ms": 60000,
                "isolation.level": "read_committed" # Offset commit strategy to ensure we only read committed messages
            }
            
            self.consumer = Consumer(config)
            self.consumer.subscribe(self.TOPICS)
            logger.info(f"✅ Kafka consumer connected to: {self.bootstrap_servers}")
            logger.info(f"   Topics: {self.TOPICS}")
            logger.info(f"   Group ID: events-to-duckdb")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Kafka: {e}")
            raise

    def start(self):
        """Start listening/consuming to Kafka events"""
        try:
            self._connect_kafka()
            logger.info("🚀 Kafka consumer started and listening for events...")

            while not self._stop_event.is_set():
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    # Check if batch flush interval has passed
                    if time.time() - self._last_flush >= self.FLUSH_INTERVAL and self._batch:
                        self._flush_batch()
                    continue

                if msg.error():
                    # Check for end of partition (not an error, just informational)
                    error_code = msg.error().code()
                    if error_code == KafkaError._PARTITION_EOF:
                        logger.debug(f"✅ End of partition for {msg.topic()}[{msg.partition()}]")
                    else:
                        logger.error(f"❌ Kafka error: {msg.error()}")
                    continue

                # Parse message
                try:
                    event_data = json.loads(msg.value().decode("utf-8"))
                    self._batch.append({
                        "event_type": msg.topic(),
                        "user_id": event_data.get("user_id"),
                        "topic": msg.topic(),
                        "event_data": event_data,
                        "event_timestamp": time.time()
                    })
                except Exception as e:
                    logger.error(f"❌ Failed to parse Kafka message: {e}")
                    continue

                # Flush if batch size is reached
                if len(self._batch) >= self.BATCH_SIZE:
                    self._flush_batch(msg)

                # Check flush interval
                if time.time() - self._last_flush >= self.FLUSH_INTERVAL:
                    self._flush_batch()

        except Exception as e:
            logger.error(f"❌ Kafka consumer encountered an error: {e}")
        finally:
            if self.consumer:
                self.consumer.close()
            logger.info("🛑 Kafka consumer stopped.")

    def _flush_batch(self, last_msg=None):
        """Write batch to DuckDB and commit Kafka offsets"""
        if not self._batch:
            return
        
        try:

            # Insert to DuckDB
            duckdb_client.insert_batch_events(self._batch)

            # Commit Kafka offset
            if last_msg and self.consumer:
                self.consumer.commit(asynchronous=False)
            
            logger.info(f"✅ Flushed batch of {len(self._batch)} events to DuckDB and committed Kafka offsets.")
            self._batch = []
            self._last_flush = time.time()

        except Exception as e:
            logger.error(f"❌ Failed to flush batch to DuckDB: {e}")

    def stop(self):
        """Stop consuming gracefully"""
        logger.info("Stopping Kafka consumer...")
        self._stop_event.set()
        if self._batch:
            self._flush_batch()


# Standalone entry point for testing
if __name__ == "__main__":
    consumer = EventConsumer()
    consumer.start()