import pandas as pd
import numpy as np
import pickle
from typing import Dict
from pathlib import Path
from tensorflow.keras.models import load_model
import logging

logger = logging.getLogger(__name__)

# Create ML Model prediction class
class MLPredictor:
    def __init__(self):
        self.models_path = Path(__file__).parent.parent.parent / "models"
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.location_maps = {}
        self.features = None

    async def load_models(self):
        """Load ML models and preprocessing objects."""
        try:
            self.models['ctat'] = pickle.load(open(self.models_path / "best_model_ctat_ultra.pkl", "rb"))
            self.models['vtat'] = pickle.load(open(self.models_path / "best_model_vtat_ultra.pkl", "rb"))
            self.models['price'] = load_model(self.models_path / "model_price_improved.keras")
            self.models['time'] = load_model(self.models_path / "model_time_improved.keras")

            # Scalers
            self.scalers['standard'] = pickle.load(open(self.models_path / "scaler.pkl", 'rb'))
            self.scalers['minmax'] = pickle.load(open(self.models_path / "scaler_minmax.pkl", 'rb'))
            self.scalers['ultra'] = pickle.load(open(self.models_path / "scaler_ultra.pkl", 'rb'))
            
            # Encoders
            self.encoders['pickup'] = pickle.load(open(self.models_path / "le_pickup.pkl", 'rb'))
            self.encoders['drop'] = pickle.load(open(self.models_path / "le_drop.pkl", 'rb'))
            
            # Location maps
            self.location_maps['pickup'] = pickle.load(open(self.models_path / "pickup_location_map.pkl", 'rb'))
            self.location_maps['drop'] = pickle.load(open(self.models_path / "drop_location_map.pkl", 'rb'))
            
            # Features list
            self.features = pickle.load(open(self.models_path / "features_ultra.pkl", 'rb'))

            logger.info("Models and preprocessing objects loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            raise e
        
    async def predict_ride_metrics(self, pickup: str, drop: str, vehicle_type: str, booking_time: str, day_of_week: int, distance_km: float) -> Dict:
        """Predict ride metrics based on input features."""
        