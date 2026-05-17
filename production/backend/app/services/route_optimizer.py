import math
from typing import List, Tuple

class RouteOptimizer:

    @staticmethod
    def haversine(lat1, lng1, lat2, lng2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = math.sin(dlat/2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
        return 2 * R * math.asin(math.sqrt(a))
    
    @staticmethod
    def shortest_path(points: List[Tuple[float, float]], start_idx: int = 0) -> List[int]:
        """TSP for waypoint ordering optimization."""
        n = len(points)
        if n == 0:
            return []
        
        visited = [False] * n
        path = [start_idx]
        visited[start_idx] = True
        current = start_idx

        for _ in range(n-1):
            next_idx = min((i for i in range(n) if not visited[i]), key=lambda i: RouteOptimizer.haversine(points[current][0], points[current][1], points[i][0], points[i][1]))
            visited[next_idx] = True
            path.append(next_idx)
            current = next_idx
        return path