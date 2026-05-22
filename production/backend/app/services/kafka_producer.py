import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from confluent_kafka import Producer, KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("⚠️ confluent_kafka library is not installed. Kafka producer will be unavailable.")

class KafkaEventProducer:
    def __init__(self):
        self.producer = None
        if KAFKA_AVAILABLE:
            self.connect()

    def connect(self):
        if not KAFKA_AVAILABLE:
            logger.warning("⚠️ Kafka producer cannot be initialized because confluent_kafka is not available.")
            return
        
        try:
            config = {
                'bootstrap_servers': settings.KAFKA_BOOTSTRAP_SERVERS,
                'client.id': 'taxi-trip-backend',
                'acks': 'all',
                'retries': 3
            }
            self.producer = Producer(config)
            logger.info(f"✅ Kafka producer connected successfully to {settings.KAFKA_BOOTSTRAP_SERVERS}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Kafka: {e}")
            self.producer = None

    def delivery_report(self, err, msg):
        """Delivery report callback"""
        if err is not None:
            logger.error(f"❌ Message delivery failed: {err}")
        else:
            logger.debug(f"✅ Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

    async def send_event(self, topic: str, event: dict):
        """Send event to Kafka topic."""
        if not KAFKA_AVAILABLE or not self.producer:
            logger.debug("⚠️ Kafka producer is not available. Event will not be sent.")
            return False

        try:
            message_value = json.dumps(event).encode('utf-8')
            self.producer.send(topic, value=message_value, callback=self.delivery_report)
            self.producer.flush(timeout=5) # Ensure the message is sent
            logger.debug(f"📤 Event sent to topic '{topic}': {event}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send event to Kafka: {e}")
            return False
        
    def close(self):
        if self.producer:
            try:
                self.producer.close()
                logger.info("🔌 Kafka producer connection closed.")
            except Exception as e:
                logger.error(f"❌ Failed to close Kafka producer connection: {e}")

# Singleton instance of KafkaEventProducer
kafka_producer = KafkaEventProducer()