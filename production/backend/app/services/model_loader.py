import pickle
import json
from pathlib import Path
import tensorflow as tf
from typing import Dict, Any

class ModelLoader:
    """Utility class to load ML models from dir."""
    def __init__(self, models_dir="./production/backend/models"):
        self.models_dir = Path(models_dir)

    # CTAT models
    def load_ctat_models(self) -> Dict[str, Any]:
        """Load all CTAT models and supporting files."""
        ctat_models = {
            'best_model': self._load_pickle('best_model_ctat_ultra.pkl'),
            'best_models_ultra': self._load_pickle('best_models_ultra_ctat.pkl'),
            'route_hour_dict': self._load_pickle('route_hour_dict_ctat.pkl'),
            'results_df': self._load_pickle('df_results_ultra_ctat.csv')
        }
        return ctat_models
    
    # VTAT models
    def load_vtat_models(self) -> Dict[str, Any]:
        """Load all VTAT models and supporting files."""
        vtat_models = {
            'best_model': self._load_pickle('best_model_vtat_ultra.pkl'),
            'best_models_ultra': self._load_pickle('best_models_ultra_vtat.pkl'),
            'route_hour_dict': self._load_pickle('route_hour_dict_vtat.pkl'),
            'results_df': self._load_pickle('df_results_ultra_vtat.csv')
        }
        return vtat_models
    
    # Price model (keras)
    def load_price_model(self):
        """Load price prediction model (Keras)."""
        try:
            model_path = self.models_dir / 'model_price_improved.keras'
            return tf.keras.models.load_model(model_path)
        except Exception as e:
            print(f"❌ Error loading price model: {e}")
            return False
        
    # TTime model (keras)
    def load_time_model(self):
        """Load time prediction model (Keras)."""
        try:
            model_path = self.models_dir / 'model_time_improved.keras'
            return tf.keras.models.load_model(model_path)
        except Exception as e:
            print(f"❌ Error loading time model: {e}")
            return False
        
    # Supporting encoders and scalers
    def load_encoders_scalers(self) -> Dict[str, Any]:
        """Load encoders and scalers for preprocessing."""
        support_files = {
            'le_pickup': self._load_pickle('le_pickup.pkl'),
            'le_drop': self._load_pickle('le_drop.pkl'),
            'pickup_location_map': self._load_pickle('pickup_location_map.pkl'),
            'drop_location_map': self._load_pickle('drop_location_map.pkl'),
            'scaler': self._load_pickle('scaler.pkl'),
            'scaler_minmax': self._load_pickle('scaler_minmax.pkl'),
            'scaler_ultra': self._load_pickle('scaler_ultra.pkl'),
        }
        return support_files
    
    # Feature processors
    def load_features(self) -> Dict[str, Any]:
        """Load feature processors"""
        features = {
            'features': self._load_pickle('features.pkl'),
            'features_new': self._load_pickle('features_new.pkl'),
            'features_ultra': self._load_pickle('features_ultra.pkl'),
        }
        return features

    # Models directory
    def load_models_dict(self):
        """Load models dictionary"""
        return self._load_pickle('models_ultra.pkl')
    
    # Config
    def load_config(self) -> Dict:
        """Load config file."""
        config_path = self.models_dir / 'config_summary.json'
        with open(config_path, 'r') as f:
            return json.load(f)
        
    # Helper method
    def _load_pickle(self, filename: str):
        """Load pickle file"""
        file_path = self.models_dir / filename
        if file_path.exists():
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        return None
    
    # Load all models
    def load_all_models(self) -> Dict[str, Any]:
        """Load all models and supporting files."""
        all_models = {
            'ctat': self.load_ctat_models(),
            'vtat': self.load_vtat_models(),
            'price': self.load_price_model(),
            'time': self.load_time_model(),
            'encoders_scalers': self.load_encoders_and_scalers(),
            'features': self.load_features(),
            'models_dict': self.load_models_dict(),
            'config': self.load_config()
        }
        return all_models