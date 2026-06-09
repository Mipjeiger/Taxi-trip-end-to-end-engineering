import pickle
import mlflow
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from .model_loader import ModelLoader

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)


class MLflowService:
    def __init__(self, tracking_uri=os.getenv("MLFLOW_TRACKING_URI"), models_dir="/app/models"):
        self.tracking_uri = tracking_uri
        self.models_dir = Path(models_dir)
        mlflow.set_tracking_uri(tracking_uri)
        self.model_loader = ModelLoader(models_dir=models_dir)

        print("=" * 60)
        print("🚀 MLFLOW INITIALIZATION")
        print("=" * 60)
        print(f"Tracking URI : {self.tracking_uri}")
        print(f"🔍 Checking models directory:  : {self.models_dir}")
        print(f"📂 Directory exists      : {self.models_dir.exists()}")

        if self.models_dir.exists():
            files = list(self.models_dir.glob("*"))
            print(f"📂 Files in directory: {files}")
        else:
            print(f"❌ Models directory does not exist: {self.models_dir}")

    def start_experiment(self, experiment_name, run_name=None):
        """Start MLFlow experiment run"""
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                mlflow.create_experiment(experiment_name)

            mlflow.set_experiment(experiment_name)

            # Verify run_name is exists by datetime
            if run_name is None:
                run_name = f"{experiment_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Run mlflow
            mlflow.start_run(run_name=run_name)
            print(f"✅ Mlflow run started: {run_name}")
            return mlflow.active_run()
        except Exception as e:
            print(f"❌ Error starting MLflow run: {e}")
            return None
    
    def end_run(self):
        try:
            mlflow.end_run()
            print("✅ Mlflow run ended")
        except Exception as e:
            print(f"❌ Error ending MLflow run: {e}")

    def experiment_has_runs(self, experiment_name):
        experiment = mlflow.get_experiment_by_name(experiment_name)
        
        if experiment is None:
            return False
        
        runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
        return len(runs) > 0
    
    def upload_file(self, file_name, artifact_path):
        file_path = (self.models_dir / file_name)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            return
        
        mlflow.log_artifact(str(file_path), artifact_path=artifact_path)
        print(f"✅ Uploaded {file_name} to MLflow at {artifact_path}")

    def register_all_models(self):
        print("\n🚀 Registering models to Mlflow...")

        # ==============================
        # CTAT Models
        # ==============================
        if not self.experiment_has_runs("CTAT_Models"):
            self.start_experiment("CTAT_Models", "ctat_registration")
            self.upload_file("best_model_ctat_ultra.pkl", "models")
            self.end_run()

        # ==============================
        # VTAT Models
        # ==============================
        if not self.experiment_has_runs("VTAT_Models"):
            self.start_experiment("VTAT_Models", "vtat_registration")
            self.upload_file("best_model_vtat_ultra.pkl", "models")
            self.end_run()

        # ==============================
        # Price Model (Keras)
        # ==============================
        if not self.experiment_has_runs("Price_Prediction"):
            self.start_experiment("Price_Prediction", "price_registration")
            self.upload_file("model_price_improved.keras", "models")
            self.end_run()

        # ==============================
        # Time Model (Keras)
        # ==============================
        if not self.experiment_has_runs("Time_Prediction"):
            self.start_experiment("Time_Prediction", "time_registration")
            self.upload_file("model_time_improved.keras", "models")
            self.end_run()

        # ==============================
        # PREPROCESSING ARTIFACTS
        # ==============================
        if not self.experiment_has_runs("Preprocessing"):
            self.start_experiment("Preprocessing", "preprocessing_registration")

            artifact_files = [
                "scaler.pkl",
                "scaler_ultra.pkl",
                "scaler_minmax.pkl",
                "le_pickup.pkl",
                "le_drop.pkl",
                "pickup_location_map.pkl",
                "drop_location_map.pkl",
                "features.pkl",
                "features_new.pkl",
                "features_ultra.pkl",
                "route_hour_dict_ctat.pkl",
                "route_hour_dict_vtat.pkl",
                "config_summary.json"
            ]
            
            for file in artifact_files:
                self.upload_file(file, "artifacts")
            
            self.end_run()
        print("✅ Model registration completed.")