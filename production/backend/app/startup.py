"""Log existing models to MLflow on startup"""
from services.mlflow_service import MLflowService

def initialize_mlflow():
    """Initialize and log all existing models to MLflow on startup."""
    try:
        mlflow_service = MLflowService(tracking_uri="http://mlflow:5005")
        print("\n" + "="*60)
        print("📦 Registering existing models with MLflow...")
        print("="*60)
        mlflow_service.log_existing_models()
        print("✅ All existing models have been registered with MLflow.")
        print("="*60 + "\n")
    except Exception as e:
        print(f"❌ Error during MLflow initialization: {str(e)}")