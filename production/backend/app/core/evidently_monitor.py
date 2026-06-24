import logging
from datetime import datetime
from typing import Dict, Any, List
import json
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class EvidentlyMonitor:
    """
    Monitor LLM responses, data quality, and system performance using Evidently AI.
    Tracks metrics for cost optimization and quality assurance.
    # TODO: Add methods for track model performance, data drift, and response quality
    """

    def __init__(self):
        self.metrics_buffer: List[Dict] = []  # Buffer to store metrics before sending to Evidently
        self.buffer_size = 100 # Flush after every 100 records

    async def log_llm_response(
        self,
        db: AsyncSession,
        **kwargs
    ):
        """Log LLM interaction for monitoring"""
        try:
            # Create a new transaction or use existing one safely
            interaction_id = str(uuid.uuid4())

            # Check if transaction is active and not aborted
            try:
                await db.execute(text("SELECT 1"))
            except Exception:
                await db.rollback()  # Rollback if transaction is aborted

            # Insert using raw SQL with proper error handling
            query = text("""
                INSERT INTO analytics.llm_interactions (
                    interaction_id,
                    user_id,
                    session_id,
                    prompt,
                    response,
                    response_time_ms,
                    tokens_used,
                    cost,
                    created_at
                ) VALUES (
                    :interaction_id,
                    :user_id,
                    :session_id,
                    :prompt,
                    :response,
                    :response_time_ms,
                    :tokens_used,
                    :cost,
                    CURRENT_TIMESTAMP
                )
            """)

            await db.execute(
                query, 
                {
                    "interaction_id": interaction_id,
                    "user_id": kwargs.get("user_id"),
                    "session_id": kwargs.get("session_id"),
                    "prompt": kwargs.get("prompt"),
                    "response": kwargs.get("response"),
                    "response_time_ms": kwargs.get("response_time_ms"),
                    "tokens_used": kwargs.get("tokens_used"),
                    "cost": kwargs.get("cost")
                }
            )
            logger.debug(f"✅ Logged LLM interaction: {interaction_id}")

        except Exception as e:
            logger.error(f"❌ Failed to log LLM response: {e}")

    async def get_llm_metrics(self, db: AsyncSession) -> Dict[str, Any]:
        """Get aggregated LLM metrics for monitoring dashboard"""
        try:
            query = text("""
                SELECT
                    COUNT(*) AS total_interactions,
                    AVG(response_time_ms) AS avg_response_time_ms,
                    MAX(response_time_ms) AS max_response_time_ms,
                    SUM(tokens_used) AS total_tokens,
                    SUM(cost) AS total_cost,
                    AVG(cost) AS avg_cost_per_interaction,
                    COUNT(DISTINCT user_id) AS unique_users,
                    COUNT(DISTINCT session_id) AS unique_sessions
                FROM analytics.llm_interactions
                WHERE created_at >= NOW() - INTERVAL '24 hours'
            """)

            result = await db.execute(query)
            row = result.fetchone()

            if not row:
                return {}
            
            return {
                "total_interactions": row[0],
                "avg_response_time_ms": float(row[1]) if row[1] else 0,
                "max_response_time_ms": row[2],
                "total_tokens": row[3],
                "total_cost": float(row[4]) if row[4] else 0,
                "avg_cost_per_interaction": float(row[5]) if row[5] else 0,
                "unique_users": row[6],
                "unique_sessions": row[7]
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to get LLM metrics: {e}")
            return {}
        
# Singleton for instance
evidently_monitor = EvidentlyMonitor()