import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

logger = logging.getLogger(__name__)

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
    """Qdrant Cloud client for semantic search & embeddings"""

    def __init__(self):
        self.api_key = os.getenv("QDRANT_API_KEY")
        self.url = os.getenv("QDRANT_CLUSTER_URL")
        self.client: Optional[QdrantClient] = None
        self.connected = False

        # Collection configuration
        self.LLM_PROMPTS_COLLECTION = "llm_prompts"
        self.TRIP_REQUESTS_COLLECTION = "trip_requests"
        self.DRIVER_PROFILES_COLLECTION = "driver_profiles"

        self._initialize()

    def _initialize(self):
        """Initialize Qdrant client connection"""
        try:
            # Connect to Qdrant Cloud
            if self.api_key:
                self.client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                    timeout=30.0
                )
                logger.info(f"✅ Connected to Qdrant at {self.url}")
            else:
                self.client = QdrantClient(":memory:")
                logger.warning("⚠️ Using in-memory Qdrant (no API key provided)")
            
            self.connected = True
            self._create_collections()
        except Exception as e:
            logger.error(f"❌ Failed to initialize Qdrant client: {e}")
            self.connected = False
            raise

    def _create_collections(self):
        """Create collections for embeddings"""
        try:
            # LLM prompts collection
            self._create_collections(
                self.LLM_PROMPTS_COLLECTION,
                vector_size=1536,
                description="LLM prompts and responses with semantic embeddings"
            )

            # Trip requests collection
            self._create_collections(
                self.TRIP_REQUESTS_COLLECTION,
                vector_size=768,
                description="Trip request descriptions with semantic embeddings"
            )

            # Driver profiles collection
            self._create_collections(
                self.DRIVER_PROFILES_COLLECTION,
                vector_size=768,
                description="Driver profile descriptions with semantic embeddings"
            )

            logger.info("✅ All Qdrant collections created or already exist.")
        except Exception as e:
            logger.error(f"❌ Failed to create Qdrant collections: {e}")

    def _create_collection(self, collection_name: str, vector_size: int, description: str):
        """Create a collection if it doesn't exist"""
        try:
            # Check if collection exists
            try:
                self.client.get_collection(collection_name)
                logger.info(f"⚠️ Collection '{collection_name}' already exists. Skipping creation.")
                return
            except:
                pass  # Collection does not exist, proceed to create

            # Create collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )
            logger.info(f"✅ Collection '{collection_name}' created successfully: {description}")
        except Exception as e:
            logger.error(f"❌ Failed to create collection '{collection_name}': {e}")

    def store_llm_prompt(self, prompt_id: str, prompt_text: str, response_text: str,
                         prompt_embedding: List[float], response_embedding: List[float],
                         metadata: Dict[str, Any]):
        """Store LLM prompt with semantic embedding for later retrieval"""
        try:
            point = PointStruct(
                id=hash(prompt_id) % 2**31,  # Use hash for ID - Generation of unique ID based on prompt_id
                vector=prompt_embedding,
                payload={
                    "prompt_id": prompt_id,
                    "prompt": prompt_text,
                    "response": response_text,
                    "response_embedding": response_embedding,
                    **metadata  # user_id, session_id, timestamp, cost, etc.
                }
            )

            self.client.upsert(
                collection_name=self.LLM_PROMPTS_COLLECTION,
                points=[point]
            )
            logger.info(f"✅ Stored LLM prompt '{prompt_id}' in Qdrant with metadata: {metadata}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to store LLM prompt '{prompt_id}' in Qdrant: {e}")
            return False
        
    def semantic_search_llm(self, query_embedding: List[float], limit: int = 5) -> List[Dict]:
        """Semantic search for LLM interactions based on query embedding"""
        try:
            results = self.client.search(
                collection_name=self.TRIP_REQUESTS_COLLECTION,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=0.7
            )

            return [{"trip_id": hit.payload.get("trip_id"), "similarity": hit.score}
                    for hit in results]
        except Exception as e:
            logger.error(f"❌ Failed to perform semantic search in Qdrant: {e}")
            return []
        
    def close(self):
        """Close Qdrant connection"""
        try:
            if self.client:
                self.client.close()
                logger.info("✅ Qdrant client connection closed.")
        except Exception as e:
            logger.error(f"❌ Failed to close Qdrant client connection: {e}")

# Singleton instance for application-wide use
qdrant_client = QdrantVectorDB()