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
    def __init__(self, tracking_uri="http://localhost:5005"):
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(tracking_uri)
        self.model_loader = ModelLoader()

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
        
    def log_params(self, params):
        """Log parameters to MLFlow"""
        try:
            mlflow.log_params(params)
            print(f"✅ Logged parameters: {params}")
        except Exception as e:
            print(f"❌ Error logging parameters: {e}")

    def log_metrics(self, metrics, step=None):
        """Log metrics to MLFlow"""
        try:
            for key, value in metrics.items():
                mlflow.log_metric(key, value, step=step)
            print(f"✅ Logged metrics: {metrics}")
        except Exception as e:
            print(f"❌ Error logging metrics: {e}")

    def log_model(self, model, artifact_path="models"):
        """Log model to MLflow"""
        try:
            if 'keras' in str(type(model)):
                mlflow.keras.log_model(model, artifact_path=artifact_path)
            else:
                mlflow.sklearn.log_model(model, artifact_path=artifact_path)
        except Exception as e:
            print(f"❌ Error logging model: {e}")

    def log_existing_models(self):
        """Log all existing models from models dir"""
        try:
            print("🔍 Logging existing models from models directory...")

            # Load CTAT models
            self.start_experiment("CTAT_Models", "ctat_models_registration")
            ctat_models = self.model_loader.load_ctat_models()
            if ctat_models['best_model']:
                self.log_model(ctat_models['best_model'], artifact_path="ctat/best_model")
            self.end_run()
            print("✅ CTAT models logged successfully.")

            # Load VTAT models
            self.start_experiment("VTAT_Models", "vtat_models_registration")
            vtat_models = self.model_loader.load_vtat_models()
            if vtat_models['best_model']:
                self.log_model(vtat_models['best_model'], artifact_path="vtat/best_model")
            self.end_run()
            print("✅ VTAT models logged successfully.")

            # Load Price model (keras)
            self.start_experiment("Price_Prediction", "price_model_registration")
            price_model = self.model_loader.load_price_model()
            if price_model:
                self.log_model(price_model, artifact_path="price_model")
            self.end_run()
            print("✅ Price model logged")

            # Load Time model (Keras)
            self.start_experiment("Time_Prediction", "time_model_registration")
            time_model = self.model_loader.load_time_model()
            if time_model:
                self.log_model(time_model, artifact_path="time_model")
            self.end_run()
            print("✅ Time model logged")
        

        except Exception as e:
            print(f"❌ Error logging existing models: {str(e)}")

    # Log artifacts method if missing
    def log_artifacts(self, local_dir, artifact_path=None):
        """Log artifacts to MLflow"""
        try:
            mlflow.log_artifacts(local_dir, artifact_path=artifact_path)
            print(f"✅ Logged artifacts from {local_dir}")
        except Exception as e:
            print(f"❌ Error logging artifacts: {str(e)}")