import numpy as np
import pandas as pd
from datetime import datetime

def create_time_features(hour: int, day_of_week: int) -> dict:
    return {
        'is_peak_hour': 1 if (7 <= hour <= 9) or (17 <= hour <= 19) else 0,
        'is_weekend': 1 if day_of_week >= 5 else 0,
        'is_night': 1 if hour >= 22 or hour <= 5 else 0,
        'hour_sin': np.sin(2 * np.pi * hour / 24),
        'hour_cos': np.cos(2 * np.pi * hour / 24),
        'day_sin': np.sin(2 * np.pi * day_of_week / 7),
        'day_cos': np.cos(2 * np.pi * day_of_week / 7),
    }

def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    # Add interaction features
    df['time_distance_interaction'] = df.get('estimated_time_min', 0) * df.get('Ride Distance', 0)
    df['price_per_km'] = df.get('estimated_price_idr', 0) / (df.get('Ride Distance', 1) + 1e-6)
    df['log_distance'] = np.log1p(df.get('Ride Distance', 0))
    df['log_price'] = np.log1p(df.get('estimated_price_idr', 0))
    return df