import numpy as np
from scipy.optimize import linear_sum_assignment
from typing import List, Dict, Any
import redis.asyncio as redis

class MatchingRecommender:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def recommend_matches(self, waiting_rides: list[dict], available_drivers: list[dict]) -> list[tuple[int, int]]:
        """Recommend matches engine on engineering recommendation principles."""
        n_rides = len(waiting_rides)
        n_drivers = len(available_drivers)
        if n_rides == 0 or n_drivers == 0:
            return []
        
        cost_matrix = np.zeros((n_rides, n_drivers))
        for i, ride in enumerate(waiting_rides):
            for j, driver in enumerate(available_drivers):
                # ETA from driver to pickup
                eta = self._estimate_eta(driver['lat'], driver['lng'],
                                                ride['pickup_lat'], ride['pickup_lng'])
                vehicle_match = 1 if driver['vehicle_type'] == ride['vehicle_type'] else 5
                rating_diff = abs(driver['rating'] - ride.get('user_rating', 4.5)) / 5.0
                cost = eta * 1.0 + vehicle_match * 2.0 + rating_diff * 1.5
                cost_matrix[i, j] = cost

            row_ind, col_ind = linear_sum_assignment(cost_matrix)
            matches = [(row_ind[k], col_ind[k]) for k in range(len(row_ind)) if cost_matrix[row_ind[k], col_ind[k]] < 50]
            return matches
        
        def _estimate_eta(self, lat1, lng1, lat2, lng2):
            # Haversine formula for distance
            import math
            R = 6371  # Earth radius in km
            dlat = math.radians(lat2 - lat1)
            dlng = math.radians(lng2 - lng1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            km = R * c
            return km / 30 * 60  # Assuming average speed of 30 km/h, return ETA in minutes