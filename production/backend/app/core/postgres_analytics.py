import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class PostgresAnalyticsClient:
    """Use existing Postgres DB for analytics queries"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.connected = False
    
    async def initialize(self):
        """Verify connection to analytics database schema"""
        try:
            await self.db.execute(text("SELECT 1"))
            self.connected = True
            logger.info("✅ Connected to Postgres Analytics database")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Postgres Analytics database: {e}")
            self.connected = False

    async def insert_batch_events(self, events: List[Dict[str, Any]]):
        """Insert batch of events into Postgres"""
        try:
            for event in events:
                await self.db.execute(text("""
                    INSERT INTO analytics.taxi_trip_data_events
                    (event_type, user_id, topic, event_data, event_timestamp)
                    VALUES (:event_type, :user_id, :topic, :event_data, :event_timestamp)
                """), event)
            await self.db.commit()
            logger.info(f"✅ Inserted {len(events)} events into Postgres Analytics")
        except Exception as e:
            logger.error(f"❌ Failed to insert events into Postgres Analytics: {e}")
            await self.db.rollback()
            raise

# Singleton instance to be used across the app
postgres_analytics_client = PostgresAnalyticsClient(db_session=None)  # db_session will be set during app startup