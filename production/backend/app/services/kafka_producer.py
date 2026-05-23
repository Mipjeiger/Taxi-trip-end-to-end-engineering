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

    def initialize(self):
        """Called explicitly from startup.py to initialize the Kafka producer connection."""
        if not KAFKA_AVAILABLE:
            logger.warning("⚠️ Kafka producer cannot be initialized because confluent_kafka is not available.")
            return
        self.connect_with_retries()

    def connect_with_retries(self, max_retries=3, delay=3):
        """Connect with retry logic."""
        for attempt in range(max_retries):
            try:
                self.connect()
                self.connected = True
                logger.info("✅ Kafka producer initialized successfully.")
                return
            except Exception as e:
                logger.warning(f"⚠️ Connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(delay)
        
        logger.warning("⚠️ Kafka connection failed after retries (non-critical)")
        self.connected = False

    def connect(self):
        try:
            config = {
                "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                "client.id": "taxi-trip-backend",
                "acks": "all",
                "retries": 3,
                "retry.backoff.ms": 500,
                "socket.timeout.ms": 10000,
                "message.timeout.ms": 10000,
                "connections.max.idle.ms": 540000
            }
            self.producer = Producer(config)
            self.admin_client = AdminClient({"bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS})
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
                NewTopic("ride-requests", num_partitions=1, replication_factor=1),
                NewTopic("frontend-events", num_partitions=1, replication_factor=1)
            ]
            fs = self.admin_client.create_topics(topics_to_create, validate_only=False)
            for topic, f in fs.items():
                try:
                    f.result(timeout=10)
                    logger.info(f"✅ Topic '{topic}' created successfully.")
                except Exception as e:
                    if "already exists" in str(e).lower() or "TopicAlreadyExists" in str(e):
                        logger.debug(f"⚠️ Topic '{topic}' already exists. Skipping creation.")
                    else:
                        logger.warning(f"❌ Failed to create topic '{topic}': {str(e)}")

        except Exception as e:
            logger.warning(f"⚠️ Topic creation skipped (non-critical): {e}")

    def delivery_report(self, err, msg):
        """Delivery report callback"""
        if err:
            logger.error(f"❌ Delivery failed [{msg.topic()}]: {err}")
        else:
            logger.debug(f"✅ Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

    async def send_event(self, topic: str, event: dict) -> bool:
        """Send event to Kafka topic."""
        if not self.producer or not self.connected:
            logger.debug(f"⚠️ Kafka unavailable, skipping {topic}")
            return False

        try:
            message_value = json.dumps(event).encode("utf-8")
            self.producer.produce(
                topic=topic,
                key=str(event.get("ride_id") or event.get("user_id") or "").encode(),
                value=message_value,
                callback=self.delivery_report
            )
            self.producer.poll(0)  # Trigger delivery report callbacks - non-blocking
            logger.debug(f"📤 Event sent to topic '{topic}': {event}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to send event to Kafka: {e}")
            return False
        
    def flush(self, timeout: int = 10):
        """Call on shutdown to drain pending message."""
        if self.producer:
            pending = self.producer.flush(timeout=timeout)
            if pending > 0:
                logger.warning(f"⚠️ {pending} messages failed to deliver before shutdown.")
        
    def close(self):
        """Close the Kafka producer connection."""
        self.flush()
        logger.info("✅ Kafka producer connection closed.")

# Singleton instance of KafkaEventProducer
kafka_producer = KafkaEventProducer()