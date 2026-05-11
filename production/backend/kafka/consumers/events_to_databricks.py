from kafka import KafkaConsumer
from databricks.sql import connect
import json
import logging
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv

# env. Configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

class EventConsumer:
    """
    Kafka consumer: Frontend events -> Databricks SQL
    Batches events every 100 messages or 30 seconds, whichever comes first.
    """

    def __init__(self, bootstrap_servers=['kafka:9092']):
        self.consumer = KafkaConsumer(
            'frontend-events',
            bootstrap_servers=bootstrap_servers,
            group_id='frontend-events-to-databricks',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )

        self.databricks_conn = connect(
            server_hostname=os.getenv('DATABRICKS_HOST'),
            token=os.getenv('DATABRICKS_TOKEN'),
            http_path=os.getenv('DATABRICKS_HTTP_PATH')
        )
        
        self.batch_events = []
        self.batch_size = 100

    def start_consuming(self):
        """Start listening/consuming to Kafka events"""
        logging.info("🚀 Starting Kafka consumer for frontend-events topic...")

        for message in self.consumer:
            event = message.value
            self.batch_events.append(event)
            logging.info(f"📥 Event: {event['event_type']} from {event['user_id']}")

            # Batch write to Databricks every 100 events
            if len(self.batch_events) >= self.batch_size:
                self.write_batch_to_databricks()

    def write_batch_to_databricks(self):
        """Write batch of events to Databricks SQL delta table"""
        if not self.batch_events:
            return
        
        try:
            cursor = self.databricks_conn.cursor()
            
            # Loop through events and inser into delta table
            for event in self.batch_events:
                query = f"""
                    INSERT INTO taxi_trip_frontend_events
                    (event_type, user_id, event_data, timestamp)
                    VALUES (
                        '{event['event_type']}',
                        '{event['user_id']}',
                        '{json.dumps(event)}',
                        '{event['timestamp']}'
                    )
                """
                cursor.execute(query)

            cursor.close()
            logging.info(f"✅ Successfully wrote batch of {len(self.batch_events)} events to Databricks")
            self.batch_events = []  # Clear batch after writing

        except Exception as e:
            logging.error(f"❌ Error writing batch to Databricks: {e}")

# Usage consumer running
if __name__ == "__main__":
    consumer = EventConsumer()
    consumer.start_consuming()