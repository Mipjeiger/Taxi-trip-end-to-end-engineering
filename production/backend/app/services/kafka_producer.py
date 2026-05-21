from kafka import KafkaProducer
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class KafkaEventProducer:
    def __init__(self):
        self.producer = None
        self.connect()

    def connect(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retries=3,
                acks='all'
            )
            logger.info("✅ Kafka producer connected successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Kafka: {e}")
            self.producer = None

    async def send_event(self, topic: str, event: dict):
        """Send event to Kafka topic."""
        try:
            if not self.producer:
                logger.warning("⚠️ Kafka producer not connected. Attempting to reconnect...")
                return False
            
            self.producer.send(topic, value=event)
            self.producer.flush() # Ensure the message is sent
            logger.debug(f"📤 Event sent to topic '{topic}': {event}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send event to Kafka: {e}")
            return False
        
    def close(self):
        if self.producer:
            self.producer.close()

# Singleton instance of KafkaEventProducer
kafka_producer = KafkaEventProducer()