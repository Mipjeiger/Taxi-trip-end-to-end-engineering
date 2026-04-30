import redis.asyncio as redis

class SurgeRecommender:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    async def recommend_action(self, location: str, current_hour: int, current_surge: float) -> dict:
        """Creating sequential recommendation with graph neural network (surge recommendation)"""
        if current_surge > 2.0:
            action = "Wait 15 min"
            message = "Surge is high. Wait for 15 minutes for potential drop."
        elif current_surge > 1.3:
            action = "wait 5 min"
            message = "Surge is moderate. Waiting for 5 minutes might help."
        else:
            action = "Book Now"
            message = "Surge is low. It's a good time to book."
        return {
            "recommendation": action,
            "confidence": 0.8,
            "current_surge": current_surge,
            "estimated_surge_after_wait": max(1.0, current_surge * 0.85),  # Dummy estimation
            "message": message
        }