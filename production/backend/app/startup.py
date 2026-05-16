import mlflow
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from app.services.model_loader import ModelLoader
from app.services.mlflow_service import MLflowService

# Load env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

def initialize_mlflow():
    """Initialize and log all existing models to MLflow"""
    try:
        mlflow_service = MLflowService(tracking_uri="http://mlflow:5005")
        print("\n" + "="*60)
        print("📦 Registering existing models with MLflow...")
        print("="*60)
        mlflow_service.log_existing_models()
        print("✅ All models registered with MLflow")
        print("="*60 + "\n")
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize MLflow: {str(e)}")