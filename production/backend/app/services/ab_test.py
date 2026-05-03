import hashlib
from typing import list, Dict, Any

class ABTest:
    def __init__(self, experiment_name: str, variants: list[str], traffic_split: list[int]):
        """traffic_split: list of percentages summing to 100, e.g. [50, 50]"""
        self.exp_name = experiment_name
        self.variants = variants
        self.split = traffic_split

    def get_variant(self, user_id: str) -> str:
        """Deterministic assignment based on user_id hash"""
        hash_val = int(hashlib.md5(f"{self.exp_name}:{user_id}".encode()).hexdigest()[:8], 16)
        bucket = hash_val % 100
        cumsum = 0
        for var, pct in zip(self.variants, self.split):
            cumsum += pct
            if bucket < cumsum:
                return var
        return self.variants[0] # fallback to first variant
    
# Example usage:
vehicle_ab = ABTest("vehicle_rec_model", ["control", "two_tower"], [50, 50])