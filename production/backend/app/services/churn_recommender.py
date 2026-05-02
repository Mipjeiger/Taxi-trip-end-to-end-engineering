import numpy as np
from typing import Dict

class ChurnRecommender:
    def __init__(self, model_path=None):
        pass

    async def recommend_promo(self, user_id: str, features: Dict) -> Dict:
        # Mock logic for churn prediction
        churn_prob = 0.1 if features.get("total_trips", 0) > 10 else 0.6
        if churn_prob > 0.5:
            return {
                "send_promo": True,
                "promo_type": "fixed_discount",
                "discount_percentage": np.random.randint(10, 35),
                "churn_probability": churn_prob,
                "expiry_hours": 48,
            }
        else:
            return {"send_promo": False, "churn_probability": churn_prob}