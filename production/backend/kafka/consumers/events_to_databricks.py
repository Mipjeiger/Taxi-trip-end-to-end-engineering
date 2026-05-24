from kafka import KafkaConsumer
from databricks.sql import connect
import json
import logging
from datetime import datetime
import threading
import time
import os
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# env. Configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

try:
    from confluent_kafka import Consumer, KafkaException
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logging.warning("⚠️ confluent_kafka library is not installed. Kafka consumer will be unavailable.")

try:
    from databricks.sql import connect as databricks_connect
    DATABRICKS_AVAILABLE = True
except ImportError:
    DATABRICKS_AVAILABLE = False
    logging.warning("⚠️ databricks-sql-connector library is not installed. Databricks connection will be unavailable.")

class EventConsumer:
    """
    Kafka consumer: Frontend events -> Databricks SQL
    Batches events every 100 messages or 30 seconds, whichever comes first.
    """

    TOPICS = ["ride-requests", "ride-events", "driver-events", "frontend-events"]
    BATCH_SIZE = 100
    FLUSH_INTERVAL = 30  # seconds

    def __init__(self, bootstrap_servers: str = None):
        self.bootstrap_servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        self.consumer = None
        self.databricks_conn = None
        self._stop_event = threading.Event()
        self._batch: list[dict] = []
        self._last_flush = time.time()

    def _connect_kafka(self):
        if not KAFKA_AVAILABLE:
            raise RuntimeError("Kafka consumer cannot be initialized because confluent_kafka is not available.")
        self.consumer = Consumer({
            "bootstrap.servers": self.bootstrap_servers,
            "group.id": "events-to-databricks",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False, # manual commit after batch is processed
            "session.timeout.ms": 30000,
            "max.poll.interval.ms": 300000
        })
        self.consumer.subscribe(self.TOPICS)
        logging.info(f"✅ Kafka consumer connected and subscribed to topics: {self.TOPICS}")

    def _connect_databricks(self):
        if not DATABRICKS_AVAILABLE:
            logger.warning("⚠️ Databricks connection cannot be initialized because databricks-sql-connector is not available.")
            return
        self.databricks_conn = databricks_connect(
            server_hostname=os.getenv("DATABRICKS_HOST"),
            http_path=os.getenv("DATABRICKS_HTTP_PATH"),
            access_token=os.getenv("DATABRICKS_TOKEN")
        )
        logging.info("✅ Connected to Databricks SQL successfully.")

    def start(self):
        """Start listening/consuming to Kafka events"""
        try:
            self._connect_kafka()
            self._connect_databricks()
        except Exception as e:
            logger.error(f"❌ Error initializing Kafka consumer or Databricks connection: {e}")
            return
        
        logger.info("🚀 EventConsumer loop started")
        try:
            while not self._stop_event.is_set():
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    self._maybe_flush()
                    continue

                if msg.error():
                    logger.error(f"❌ Kafka error: {msg.error()}")
                    continue

                try:
                    event = json.loads(msg.value().decode('utf-8'))
                    event["_topic"] = msg.topic()
                    event["_partition"] = msg.partition()
                    event["_offset"] = msg.offset()
                    self._batch.append(event)
                    logger.debug(f"📥 [{msg.topic()}] {event.get('event_type')} "
                                 f"user={event.get('user_id')}")
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Failed to decode JSON from message on topic {msg.topic()} : {msg.value()}")

                if len(self._batch) >= self.BATCH_SIZE:
                    self._flush_batch(msg)
                
                self._maybe_flush(msg)

        except Exception as e:
            logger.error(f"❌ Error in Kafka consumer loop: {e}")
        finally:
            self._flush_batch()
            if self.consumer:
                self.consumer.close()
            if self.databricks_conn:
                self.databricks_conn.close()
            logger.info("🛑 Kafka consumer stopped.")

    def maybe_flush(self, last_msg=None):
        """Flush batch if FLUSH_INTERVAL has passed since last flush."""
        if time.time() - self._last_flush >= self.FLUSH_INTERVAL and self._batch:
            self._flush_batch(last_msg)

    def flush_batch(self, last_msg=None):
        """Insert batch of events info Databricks and commit Kafka offsets."""
        if not self._batch:
            return
        try:
            self._write_to_databricks(self._batch)
            # Commit only after successful write to avoid data loss
            if last_msg and self.consumer:
                self.consumer.commit(message=last_msg)
            self._batch.clear()
            self._last_flush = time.time()
        except Exception as e:
            logger.error(f"❌ Failed to flush batch to Databricks: {e}")

    def _write_to_databricks(self, events: list[dict]):
        if not self.databricks_conn:
            # Databricks not available - log and skip
            logger.info(f"⚠️ Databricks connection not available. Skipping write of {len(events)} events.")
            return
        
        cursor = self.databricks_conn.cursor()
        try:
            # Parameterized query - no SQL injection risk
            insert_sql = """
                INSERT INTO taxi_trip_frontend_events
                    (event_type, user_id, topic, event_data, event_timestamp)
                    VALUES (?, ?, ?, ?, ?)
            """
            rows = [
                (
                    event.get("event_type", "unknown"),
                    event.get("user_id", ""),
                    event.get("_topic", ""),
                    json.dumps(event),
                    event.get("timestamp", time.time())
                )
                for event in events
            ]
            cursor.executemany(insert_sql, rows)
            logger.info(f"✅ Flushed {len(events)} events to Databricks successfully.")
        finally:
            cursor.close()

# Standalone entry point
if __name__ == "__main__":
    consumer = EventConsumer()
    consumer.start()