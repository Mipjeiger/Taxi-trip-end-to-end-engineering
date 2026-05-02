import pandas as pd
import networkx as nx
import numpy as np
import math
from typing import List, Dict, Tuple, Optional
from app.core.config import DATABASE_PATH

class RouteRecommender:
    def __init__(self, graph_path: Optional[str] = None):
        self.data = pd.read_parquet(DATABASE_PATH)
        self.graph = self._build_graph_from_df(self.data) if not graph_path else  nx.read_pickle(graph_path)

    def _haversine(self, lat1, lng1, lat2, lng2) -> float:
        R = 6371 # Earth radius
        dlat, dlng = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
        return R * 2 * math.asin(math.sqrt(a))
    
    def _build_graph_from_df(self, df: pd.DataFrame) -> nx.Graph:
        G = nx.DiGraph()
        route_stats = (
            df.groupby(["Pickup Encoded", "Dropoff Encoded", "route_cluster"])
        .agg(
            avg_ctat=("route_ctat_mean", "mean"),
            avg_vtat=("route_vtat_mean", "mean"),
            avg_distance=("Ride Distance", "mean"),
            avg_price=("Booking Value", "mean"),
            avg_traffic=("traffic_score", "mean"),
            demand=("route_demand", "mean"),
            complexity=("route_complexity", "mean"),
            count=("Booking ID", "count"),
        ).reset_index()
        )
        for _, row in route_stats.iterrows():
            G.add_edge(
                row["Pickup Encoded"], row["Drop Encoded"],
                route_cluster=row["route_cluster"],
                avg_ctat=row["avg_ctat"], avg_vtat=row["avg_vtat"],
                avg_distance=row["avg_distance"], avg_price=row["avg_price"],
                avg_traffic=row["avg_traffic"], demand=row["demand"],
                complexity=row["complexity"], count=row["count"]
            )
        
        return G
    
    def _derive_time_features(self, dt: pd.Timestamp) -> Dict:
        h, dow = dt.hour, dt.dayofweek
        return {
            "hour": h, "minute": dt.minute, "day_of_week": dow,
            "hour_sin": np.sin(2 * np.pi * h / 24),
            "hour_cos": np.cos(2 * np.pi * h / 24),
            "dow_sin": np.sin(2 * np.pi * dow / 7),
            "dow_cos": np.cos(2 * np.pi * dow / 7),
            "is_peak_hour": int(7 <= h <= 9 or 17 <= h <= 19),
            "is_night": int(h >= 22 or h < 5),
            "is_weekend": int(dow >= 5)
        }
    
    def _derive_distance_features(self, distance: float) -> Dict:
        return {
            "distance": np.log1p(distance),
            "distance_squared": distance ** 2,
            "distance_sqrt": np.sqrt(distance),
            "distance_bin": pd.cut([distance], bins=[0,5,10,20,50,9999],
                                   labels=["very_short", "short", "medium", "long", "very_long"])[0]
        }
    
    def _score_route(self, edge_data: Dict, time_features: Dict, preferences: Dict) -> float:
        w = {k: preferences.get(k, d) for k, d in [
            ("weight_time", 0.4), ("weight_cost", 0.3),
            ("weight_traffic", 0.2), ("weight_complexity", 0.1)
        ]}
        peak = 1.3 if time_features["is_peak_hour"] else 1.0
        score = (
            w["weight_time"] * edge_data["avg_ctat"]
            + w["weight_cost"] * edge_data["avg_price"]
            + w["weight_traffic"] * edge_data["avg_traffic"] * peak
            + w["weight_complexity"] * edge_data["complexity"]
        )
        return round(score, 4)
    
    def _get_historical_context(self, pickup_enc: int, drop_enc: int, hour: int, dow: int) -> Dict:
        df = self.data
        mask = (df["Pickup Encoded"] == pickup_enc) & (df["Dropoff Encoded"] == drop_enc) & (df["hour"] == hour)
        subset = df[mask] if not df[mask].empty else df[(df["Pickup Encoded"] == pickup_enc) & (df["Dropoff Encoded"] == drop_enc)]
        if subset.empty:
            return {}
        return {k: subset[v].mean() for k, v in {
            "route_ctat_mean": "route_ctat_mean", "route_vtat_mean": "route_vtat_mean",
            "hourly_demand": "hourly_demand", "demand_pressure": "demand_pressure",
            "traffic_score": "traffic_score", "estimated_pickup_time_minute": "estimated_pickup_time_minute",
            "estimated_drop_time_minute": "estimated_drop_time_minute", "price_per_km": "price_per_km",
            "driver_score": "driver_score", "avg_rating": "avg_rating",
            "route_complexity": "route_complexity",
        }.items() | {"sample_count": len(subset)}}
    
    async def recommend_route(
            self,
            lat1: float, lng1: float,
            lat2: float, lng2: float,
            datetime_str: str,
            pickup_encoded: int,
            drop_encoded: int,
            user_preferences: Optional[Dict] = None,
            vehicle_type: Optional[str] = None
    ) -> Dict:
        preferences = user_preferences or {}