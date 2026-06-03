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
        user_id: str,
        session_id: str,
        prompt: str,
        response: str,
        response_time_ms: int,
        tokens_used: int,
        cost: float,
        model: str = "llama-3.1-8b-instant"
    ):
        """Log LLM interaction for monitoring"""
        try:
            metric = {
                "user_id": user_id,
                "session_id": session_id,
                "prompt": prompt,
                "response": response,
                "response_time_ms": response_time_ms,
                "tokens_used": tokens_used,
                "cost": cost,
                "model": model,
                "timestamp": datetime.utcnow().isoformat() # Optional: for time-based post-processing in Evidently
            }

            # Store in analytics database
            insert_query = text("""
                INSERT INTO analytics.llm_interactions
                (interaction_id , user_id, session_id, prompt, response, response_time_ms, tokens_used, cost, created_at)
                VALUES (:interaction_id, :user_id, :session_id, :prompt, :response, :response_time_ms, :tokens_used, :cost, CURRENT_TIMESTAMP)
            """)
            
            await db.execute(insert_query, {
                "interaction_id": str(uuid.uuid4()),
                "user_id": user_id,
                "session_id": session_id,
                "prompt": prompt,
                "response": response,
                "response_time_ms": response_time_ms,
                "tokens_used": tokens_used,
                "cost": cost
            })
            await db.commit()
            logger.debug(f"✅ Logged LLM response for user {user_id} in session {session_id}")

        except Exception as e:
            logger.error(f"❌ Failed to log LLM response: {e}")
            await db.rollback()

    async def get_llm_metrics(self, db: AsyncSession) -> Dict[str, Any]:
        """Get aggregated LLM metrics for monitoring dashboard"""
        try:
            query = text("""
                SELECT
                    COUNT(*) as total_interactions,
                    AVG(response_time_ms) as avg_response_time_ms,
                    MAX(response_time_ms) as max_response_time_ms,
                    SUM(tokens_used) as total_tokens,
                    SUM(cost) as total_cost,
                    AVG(cost) as avg_cost_per_interaction,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT session_id) as unique_sessions
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