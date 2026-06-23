import pickle
import json
import os
from pathlib import Path
#import tensorflow as tf
from typing import Dict, Any
from dotenv import load_dotenv

# Configuration .env
BASE_DIR = Path(__file__).parent.parent.parent.parent 
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

class ModelLoader:
    """Utility class to load ML models from dir."""
    def __init__(self, models_dir: str = None):
        
        if models_dir is not None:
            self.models_dir = Path(models_dir)
        else:
            possible_paths = [
               '/app/models',                    # Docker backend
               '/app/backend/models',             # Local development
               '/backend/models',                 # Alternative local
                '/opt/airflow/backend/models',    # Docker Airflow
                '/opt/airflow/models',            # Alternative Airflow
                #'./models',                       # Local
                #'../models',                      # Local relative
            ]
            
            self.models_dir = None
            for path in possible_paths:
                if Path(path).exists() and any(Path(path).iterdir()):
                    self.models_dir = Path(path)
                    print(f"✅ Found models directory: {self.models_dir}")
                    break

            if self.models_dir is None:
                # Last resort: check env variable
                env_path = os.getenv('MODELS_PATH')
                if env_path and Path(env_path).exists():
                    self.models_dir = Path(env_path)
                    print(f"✅ Found models directory from env: {self.models_dir}")
                else:
                    self.models_dir = Path('/opt/airflow/models')
                    print(f"⚠️ Warning: No models directory found in standard paths. Defaulting to {self.models_dir}. Please check the path.")
                
        if not self.models_dir.exists():
            print(f"⚠️ Warning: Models directory {self.models_dir} does not exist. Please check the path.")
        else:
            files = list(self.models_dir.iterdir())
            print(f"✅ Models directory: {self.models_dir} ({len(files)} files)")

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
            #return tf.keras.models.load_model(model_path)
            return None
        except Exception as e:
            print(f"❌ Error loading price model: {e}")
            return False
        
    # TTime model (keras)
    def load_time_model(self):
        """Load time prediction model (Keras)."""
        try:
            model_path = self.models_dir / 'model_time_improved.keras'
            #return tf.keras.models.load_model(model_path)
            return None
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
    
    def load_config(self) -> Dict:
        config_path = self.models_dir / 'config_summary.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        print(f"⚠️ Warning: Config file {config_path} does not exist.")
        return {}
    
    # Config
    def load_config(self) -> Dict:
        """Load config file."""
        config_path = self.models_dir / 'config_summary.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        print(f"⚠️ Warning: Config file {config_path} does not exist.")
        return {}

    # Helper method
    def _load_pickle(self, filename: str):
        """Load pickle file"""
        file_path = self.models_dir / filename
        if not file_path.exists():
            print(f"⚠️ Warning: Pickle file {file_path} does not exist.")
            return None
        try:
            with open(file_path, 'rb') as f:
                obj = pickle.load(f)
            print(f"✅ Successfully loaded {file_path}")
            return obj
            
        except Exception as e:
            print(f"❌ Error occurred while loading {file_path}: {e}")
            return None
    
    # Load all models
    def load_all_models(self) -> Dict[str, Any]:
        """Load all models and supporting files."""
        all_models = {
            'ctat': self.load_ctat_models(),
            'vtat': self.load_vtat_models(),
            #'price': self.load_price_model(),
            #'time': self.load_time_model(),
            'encoders_scalers': self.load_encoders_scalers(),
            'features': self.load_features(),
            'models_dict': self.load_models_dict(),
            'config': self.load_config()
        }
        return all_models
    

# Singletone
model_loader = ModelLoader()