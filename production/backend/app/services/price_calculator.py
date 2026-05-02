import numpy as np
from typing import Dict

class PriceCalculator:
    @staticmethod
    def calculate(distance_km: float, time_min: float, base_fare: float = 7000, per_km: float = 2900, per_min: float = 1200, surge_multiplier: float = 1.0) -> float:
        return (base_fare + distance_km * per_km + time_min * per_min) * surge_multiplier
    
    @staticmethod
    def get_surge_factor(hour: int, demand_factor: float = 1.0) -> float:
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            surge = 1.5
        elif (hour >= 22 or hour <= 5):
            surge = 1.2
        else:
            surge = 1.0
        return surge * demand_factor