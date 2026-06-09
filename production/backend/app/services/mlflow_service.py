import pickle
import mlflow
import mlflow.sklearn
import os
import pandas as pd
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

    def log_metrics_from_csv(self, csv_name):
        """Extract metrics from result CSV."""
        try:
            csv_path = self.models_dir / csv_name

            if not csv_path.exists():
                print(f"❌ Metrics CSV not found: {csv_path}")
                return
            
            df = pd.read_csv(csv_path)
            print(df.head())

            # Extract numeric columns for logging
            numeric_cols = df.select_dtypes(include=['number']).columns

            metrics = {}

            for col in numeric_cols:
                metrics[col] = float(df[col].mean())

            mlflow.log_metrics(metrics) # Log all metrics for models
            print(f"✅ Successfully logged metrics from {csv_name} to MLflow: {metrics}")

        except Exception as e:
            print(f"❌ Error logging metrics from {csv_name}: {e}")

    def register_sklearn_model(
            self,
            experiment_name: str,
            run_name: str,
            model_filename: str,
            metrics_csv: str = None
    ):
        """Register sklearn model into MLflow Registry."""
        model_path = self.models_dir / model_filename

        if not model_path.exists():
            print(f"❌ Model file not found: {model_path}")
            return
        
        # Load the models with open
        with open(model_path, "rb") as f:
            model = pickle.load(f)

        self.start_experiment(experiment_name, run_name=run_name)

        # ------------------------------------------------
        # Parameters
        # ------------------------------------------------
        mlflow.log_param("model_file", model_filename)
        mlflow.log_param("experiment", experiment_name)

        # ------------------------------------------------
        # Metrics
        # ------------------------------------------------
        if metrics_csv:
            self.log_metrics_from_csv(metrics_csv)

        # ------------------------------------------------
        # Register actual model
        # ------------------------------------------------
        model_info = mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model"
        )

        try:
            mlflow.register_model(
                model_uri=model_info.model_uri,
                name=experiment_name
            )
            print(f"✅ Successfully registered model {model_filename} to MLflow under experiment {experiment_name}")
        
        except Exception as e:
            print(f"❌ Error registering model {model_filename} to MLflow: {e}")

        self.end_run()
    
    def register_all_models(self):
        """
        Register all models and artifacts to MLflow.
        Safely checks with logging detailed.
        """
        print("=" * 60)
        print("🚀 REGISTERING ALL MODELS")
        print("=" * 60)

        # ------------------------------------------------
        # CTAT Models
        # ------------------------------------------------
        if not self.experiment_has_runs("CTAT_Models"):
            print("🚀 Registered CTAT Models")
            self.register_sklearn_model(
                experiment_name="CTAT_Models",
                run_name="ctat_registration",
                model_filename="best_model_ctat_ultra.pkl",
                metrics_csv="df_results_ultra_ctat.csv"
            )

        # ------------------------------------------------
        # VTAT Models
        # ------------------------------------------------
        if not self.experiment_has_runs("VTAT_Models"):
            print("🚀 Registered VTAT Models")
            self.register_sklearn_model(
                experiment_name="VTAT_Models",
                run_name="vtat_registration",
                model_filename="best_model_vtat_ultra.pkl",
                metrics_csv="df_results_ultra_vtat.csv"
            )
        
        # ------------------------------------------------
        # Preprocessing
        # ------------------------------------------------
        if not self.experiment_has_runs("Preprocessing"):
            self.start_experiment("Preprocessing", run_name="preprocessing_registration")

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

            for file_name in artifact_files:
                try:
                    self.upload_file(file_name, artifact_path="preprocessing")

                except Exception as e:
                    print(f"❌ Error uploading {file_name} to MLflow: {e}")

            self.end_run()

        print("✅ All models and artifacts registered to MLflow successfully.")