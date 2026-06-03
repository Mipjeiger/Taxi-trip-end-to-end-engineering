from email.mime import text
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sqlalchemy import text

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR.parent / '.env'
logger.info(f"✅ Loaded environtment variables from: {ENV_PATH}")

if not ENV_PATH.exists():
    ENV_PATH = BASE_DIR / '.env'
    logging.debug(f"⚠️ .env file not found at {ENV_PATH}, trying fallback location: {ENV_PATH}")

load_dotenv(dotenv_path=ENV_PATH)

# ================================================================
# Qdrant Client for Vector Search and Similarity
# ================================================================
class QdrantVectorDB:
    """
    Pure Qdrant client.

    No embedding model
    No sentence transformer
    No torch

    Accept vectors generated elsewhere
    """

    def __init__(self):
        self.client = None
        self._initialize()

    def _initialize(self):
        """Initialize Qdrant client connection"""
        try:
            qdrant_host = os.getenv("QDRANT_CLUSTER_URL")
            qdrant_api_key = os.getenv("QDRANT_API_KEY")

            self.client = QdrantClient(
                url=qdrant_host,
                api_key=qdrant_api_key,
                timeout=30
            )

            logger.info(f"✅ Connected to Qdrant at {qdrant_host}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Qdrant client: {e}")
            raise

    def create_collection(self, collection_name: str, vector_size: int = 784):
        """Create a vector collection for storing embeddings"""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            existing_names = [col.name for col in collections.collections]

            if collection_name in existing_names:
                logger.info(f"⚠️ Collection '{collection_name}' already exists. Skipping creation.")
                return
            
            # Create new collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE # Cosine similarity for semantic search
                )
            )
            logger.info(f"✅ Collection '{collection_name}' created successfully.")
            logger.info(f"📊 Collection '{collection_name}' vector size: {vector_size}, distance metric: COSINE")

        except Exception as e:
            logger.error(f"❌ Failed to create Qdrant collections: {e}")
            raise

    def add_point(
        self,
        collection_name: str,
        point_id: str,
        vector: List[float],
        metadata: Dict[str, Any]
    ):
        """Insert vector directly.

        Vector comes from:
        - Groq
        - OpenAI
        - VoyageAI
        - Jina
        - Ollama
        - etc."""
        try:

            logger.info(f"🔍 Adding point to collection '{collection_name}' with ID '{point_id}' and metadata: {metadata}")
            logger.info(f"🔍 Vector length: {len(vector)} (should match collection vector size)")

            # Assuming vector is provided directly (not generated from text)
            point = PointStruct(
                id=int(point_id) if str(point_id).isdigit() else abs(hash(point_id)) % (10**9), # Ensure numeric ID for Qdrant
                vector=vector,
                payload=metadata # Store metadata for filtering and retrieval
            )

            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            logger.info(f"✅ Added point '{point_id}' to collection '{collection_name}' with metadata: {metadata}")

        except Exception as e:
            logger.error(f"❌ Failed to add point to Qdrant: {e}")
            raise

    def search_vector(
            self,
            collection_name: str,
            query_vector: List[float],
            limit: int = 5,
            score_threshold: float = 0.5
    ):
        """Search for similar vectors in the collection"""
        try:
            logger.info(f"🔍 Searching for similar vectors in collection '{collection_name}' with query vector length: {len(query_vector)}")

            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold # Minimum similarity score to consider
            )
            logger.info(f"🔍 Found {len(results)} similar vectors in collection '{collection_name}'")

            return [
                {
                    "id": result.id,
                    "score": result.score,
                    "metadata": result.payload
                }
                for result in results
            ]
        
        except Exception as e:
            logger.error(f"❌ Failed to search similar vectors in Qdrant: {e}")
            raise

    # Delete collection (for testing and cleanup)
    def delete_collection(self, collection_name: str):
        try:
            self.client.delete_collection(collection_name=collection_name)
            logger.info(f"✅ Collection '{collection_name}' deleted successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to delete collection '{collection_name}': {e}")
            raise

# Singleton instance for application-wide use
qdrant_vector_db = QdrantVectorDB()