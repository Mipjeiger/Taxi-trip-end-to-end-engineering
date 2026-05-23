import json
import logging
import time
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from confluent_kafka import Producer, KafkaError
    from confluent_kafka.admin import AdminClient, NewTopic
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("⚠️ confluent_kafka library is not installed. Kafka producer will be unavailable.")

class KafkaEventProducer:
    def __init__(self):
        self.producer = None
        self.admin_client = None
        self.connected = False
        if KAFKA_AVAILABLE:
            self.connect_with_retries()

    def connect_with_retries(self, max_retries=3):
        """Connect with retry logic."""
        for attempt in range(max_retries):
            try:
                self.connect()
                self.connected = True
                return
            except Exception as e:
                logger.warning(f"⚠️ Connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        logger.warning("⚠️ Kafka connection failed after retries (non-critical)")
        self.connected = False

    def connect(self):
        if not KAFKA_AVAILABLE:
            logger.warning("⚠️ Kafka producer cannot be initialized because confluent_kafka is not available.")
            return
        
        try:
            config = {
                "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                "client.id": "taxi-trip-backend",
                "acks": "all",
                "retries": 3,
                "socket.timeout.ms": 60000,
                "connections.max.idle.ms": 540000
            }
            self.producer = Producer(config)
            self.admin_client = AdminClient(config)
            logger.info(f"✅ Kafka producer connected successfully to {settings.KAFKA_BOOTSTRAP_SERVERS}")

            # Create topics
            self._create_topics()

        except Exception as e:
            logger.error(f"❌ Failed to connect to Kafka: {e}")
            raise

    def _create_topics(self):
        """Create Kafka topics if they don't exist.
            returns if topics were created, just use the current topics."""
        if not self.admin_client:
            logger.debug("⚠️ Kafka admin client is not available. Cannot create topics.")
            return
        
        try:
            topics_to_create = [
                NewTopic("driver-events", num_partitions=1, replication_factor=1),
                NewTopic("ride-events", num_partitions=1, replication_factor=1),
                NewTopic("ride-requests", num_partitions=1, replication_factor=1)
            ]
            fs = self.admin_client.create_topics(topics_to_create, validate_only=False)

            for topic, f in fs.items():
                try:
                    f.result(timeout=10)
                    logger.info(f"✅ Topic '{topic}' created successfully.")
                except Exception as e:
                    error_msg = str(e)
                    if "TopicAlreadyExistsError" in error_msg or "already exists" in error_msg:
                        logger.debug(f"⚠️ Topic '{topic}' already exists.")
                    else:
                        logger.warning(f"❌ Failed to create topic '{topic}': {error_msg}")
        
        except Exception as e:
            logger.warning(f"⚠️ Topic creation skipped (non-critical): {e}")

    def delivery_report(self, err, msg):
        """Delivery report callback"""
        if err:
            logger.error(f"❌ Message delivery failed: {err}")

    async def send_event(self, topic: str, event: dict) -> bool:
        """Send event to Kafka topic."""
        if not self.producer or not self.connected:
            logger.debug(f"⚠️ Kafka unavailable, skipping {topic}")
            return False

        try:
            message_value = json.dumps(event).encode("utf-8")
            self.producer.produce(
                topic,
                value=message_value,
                callback=self.delivery_report
            )
            self.producer.flush(timeout=5)
            logger.debug(f"📤 Event sent to topic '{topic}': {event}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send event to Kafka: {e}")
            return False
        
    def close(self):
        """Close the Kafka producer connection."""
        if self.producer:
            try:
                self.producer.flush(timeout=10)
                logger.info("🔌 Kafka producer connection closed.")
            except Exception as e:
                logger.error(f"❌ Failed to close Kafka producer connection: {e}")

# Singleton instance of KafkaEventProducer
kafka_producer = KafkaEventProducer()