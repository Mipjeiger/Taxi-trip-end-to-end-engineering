import logging
import json
import threading
import time
import uuid
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import List

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

# Dependencies for PostgreSQL insertion
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")

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
                "group.id": "events-to-postgres",
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
            logger.info(f"✅ Kafka consumer connected | topics: {self.TOPICS}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Kafka: {e}")
            raise

    def _insert_batch_postgres(self, batch: List[dict]):
        """
        Insert batch of events into analytics.taxi_trip_data_events (Postgresql database) using psycopg2.
        Uses a sync connection since this runs in a background thread (not async context).
        Matches schema: -> Postgresql Database on analytics.taxi_trip_data_events
        """
        import psycopg2
        import psycopg2.extras
        

        conn = None
        try:
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD
            )

            with conn.cursor() as cur:
                # User execute_values for efficient batch insert
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO analytics.taxi_trip_data_events
                    (event_id, event_type, user_id, topic, event_data, event_timestamp)
                    VALUES %s
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    [
                        (
                            str(uuid.uuid4()), # event_id
                            row.get("event_type", "unknown"), # event_type
                            row.get("user_id"), # user_id
                            row.get("topic", "unknown"), # topic
                            json.dumps(row.get("event_data", {})), # event_data (JSON)
                            row.get("event_timestamp", time.time()) # event_timestamp
                        )
                        for row in batch
                    ],
                )
            conn.commit()
            logger.info(f"✅ Inserted batch of {len(batch)} events into Postgres.")

        except Exception as e:
            logger.error(f"❌ Failed to insert batch into Postgres: {e}")
            if conn:
                conn.rollback()
            raise

        finally:
            if conn:
                conn.close()

    def start(self):
        """Start listening/consuming to Kafka events"""
        try:
            self._connect_kafka()
            logger.info("🚀 Kafka consumer started and listening for events...")

            while not self._stop_event.is_set():
                msg = self.consumer.poll(timeout=1.0)

                # No message - check flush interval
                if msg is None:
                    if time.time() - self._last_flush >= self.FLUSH_INTERVAL and self._batch:
                        self._flush_batch()
                    continue
                
                # Kafka error handling
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug(f"✅ End of partition for {msg.topic()}[{msg.partition()}]")
                    else:
                        logger.error(f"❌ Kafka error: {msg.error()}")
                    continue

                # Parse and batch message
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
                    self._flush_batch(last_msg=msg)

                # Flush on time interval
                elif time.time() - self._last_flush >= self.FLUSH_INTERVAL:
                    self._flush_batch(last_msg=msg)

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
            self.insert_batch_postgres(self._batch)

            # Commit Kafka offset after successful Database written
            if last_msg and self.consumer:
                self.consumer.commit(asynchronous=False)
            
            logger.info(f"✅ Flushed batch of {len(self._batch)} events to Postgres and committed Kafka offsets.")
            self._batch = []
            self._last_flush = time.time()

        except Exception as e:
            logger.error(f"❌ Flush failed — batch retained for retry: {e}")
            # Don't clear batch or commit offset on failure → retry next flush
            
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