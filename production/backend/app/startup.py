from pathlib import Path
from dotenv import load_dotenv
import logging
import os
import mlflow

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

async def initialize_mlflow():
    """Initialize and log all existing models to MLflow"""

    try:
    # Check models dir
        models_dir = Path("/app/models")
        if not models_dir.exists():
            logger.warning(f"⚠️ Models directory not found at {models_dir}")
        else:
            model_files = list(models_dir.glob("*.keras")) + list(models_dir.glob("*.pkl"))
            logger.info(f"📂 Found {len(model_files)} model files in {models_dir}")
            
            # Loop through and log each model
            for model_file in model_files:
                logger.info(f"   - {model_file.name}")

        # MLflow init with timeout
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001"))
        logger.info(f"🔗 Connected to MLflow at {mlflow.get_tracking_uri()}")
    
    except Exception as e:
        logger.error(f"❌ MLflow initialization failed: {str(e)}")
        raise