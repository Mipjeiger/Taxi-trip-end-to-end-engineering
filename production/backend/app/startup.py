from pathlib import Path
from dotenv import load_dotenv
from app.services.mlflow_service import MLflowService
import logging
import os

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

async def initialize_mlflow():
    """Initialize and log all existing models to MLflow"""

    # Check models dir
    models_dir = Path("/app/models")
    if not models_dir.exists():
        logger.warning(f"⚠️ Models directory not found at {models_dir}")
    else:
        model_files = list(models_dir.glob("*.keras")) + list(models_dir.glob("*.pkl"))
        logger.info(f"📂 Found {len(model_files)} model files in {models_dir}")
        for model_file in model_files:
            logger.info(f"   - {model_file.name}")

    # Rest of mlflow init
    try:
        import mlflow
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
        logger.info(f"✅ Connected to MLflow at {os.getenv('MLFLOW_TRACKING_URI')}")
    except Exception as e:
        logger.warning(f"⚠️  Warning: MLflow not initialized: {str(e)}")