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
    
    def upload_file(self, filename: str, artifact_path: str = "models"):
        """Upload file as MLflow artifact"""
        
        file_path = (self.models_dir / filename)
        print(f"🚀 Starting upload: {file_path}")
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        print(f"🚀 Starting upload: {filename}")
        mlflow.log_artifact(str(file_path), artifact_path=artifact_path)
        print(f"✅ Successfully uploaded {filename} to MLflow under {artifact_path}")

    def register_all_models(self):
        """
        Register all models and artifacts to MLflow.
        Safely checks with logging detailed.
        """
        print("🚀 Starting model registration to MLflow...")

        registrations = [
            {
                "experiment": "CTAT_Models",
                "run_name": "ctat_registration",
                "files": ["best_model_ctat_ultra.pkl"],
                "artifact_path": "models"
            },
            {
                "experiment": "VTAT_Models",
                "run_name": "vtat_registration",
                "files": ["best_model_vtat_ultra.pkl"],
                "artifact_path": "models"
            },
            {
                "experiment": "Preprocessing",
                "run_name": "preprocessing_registration",
                "files": [
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
                ],
                "artifact_path": "artifacts"
            }
        ]

        for reg in registrations:
            experiment_name = reg["experiment"]

            try:
                print(f"\n{'=' * 60}")
                print(f"📦 Processing experiment: {experiment_name}")
                print(f"{'=' * 60}")

                if self.experiment_has_runs(experiment_name):
                    print(f"⏩ Skipping {experiment_name} (already registered)")
                    continue

                self.start_experiment(experiment_name, run_name=reg["run_name"])

                for file_name in reg["files"]:
                    
                    try:
                        file_path = self.models_dir / file_name
                        print(f"📤 Uploading {file_name}...")
                        print(f"📁 Full path: {file_path}")

                        if not file_path.exists():
                            print(f"❌ File not found: {file_path}")
                            continue

                        self.upload_file(file_name, artifact_path=reg["artifact_path"])
                        print(f"✅ Successfully uploaded {file_name} to {experiment_name}")

                    except Exception as e:
                        print(f"❌ Error uploading {file_name} to {experiment_name}: {e}")

                # End the MLflow run after processing all files for the experiment
                self.end_run()
                print(f"✅ Completed registration for {experiment_name}")

            except Exception as e:
                print(f"❌ Error processing experiment {experiment_name}: {e}")

                try:
                    self.end_run()
                except:
                    pass

        print("\n🚀 Model registration process completed.")