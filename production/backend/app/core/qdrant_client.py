import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
from qdrant_client.http import models
from qdrant_client import QdrantClient
from app.core.config import settings
from qdrant_client.models import Distance, VectorParams

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
        self.connected = False
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Qdrant client connection"""
        try:
            # Use primary Qdrant cloud
            if settings.QDRANT_URL and settings.QDRANT_URL.strip():                
                self.client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY,
                    timeout=60
                )
            else:
                logger.info("⚠️ Qdrant connection details not fully configured. Skipping Qdrant initialization.")
                self.client = QdrantClient(
                    host="localhost",
                    port=6333,
                    timeout=60
                )

            # Test connection without logging sensitive details data
            self.client.get_collections()
            self.connected = True
            logger.info("✅ Successfully connected to Qdrant vector database.")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Qdrant client: {e}")
            self.connected = False
            self.client = None

    def create_collection(self, collection_name: str, vector_size: int = 384):
        """Create a new collection for storing embeddings"""
        try:
            if not self.client:
                logger.error("❌ Qdrant client is not initialized. Cannot create collection.")
                return

            # Get existing collections
            collections = self.client.get_collections().collections
            existing_names = [col.name for col in collections]

            if collection_name in existing_names:

                # Check vector size
                collection_info = self.client.get_collection(collection_name)
                existing_size = collection_info.config.params.vectors.size

                if existing_size != vector_size:
                    logger.warning(f"⚠️ Collection '{collection_name}' already exists with different vector size ({existing_size}). Consider deleting and recreating if this is an issue.")
                

                    # Delete old collection
                    self.client.delete_collection(collection_name=collection_name)
                    logger.info(f"🗑️ Deleted existing collection '{collection_name}' to create a new one.")

                    # Create new collection
                    self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=models.VectorParams(
                            size=vector_size,
                            distance=models.Distance.COSINE # Cosine similarity for semantic search
                        )
                    )
                else:
                    logger.debug(f"📂 Collection '{collection_name}' does not exist. Creating new collection.")

            else:

                # Create new collection
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE # Cosine similarity for semantic search
                    )
                )
                logger.info(f"✅ Created collection '{collection_name}'")
            
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create Qdrant collections: {type(e).__name__}")
            
            return False

    def search_vector(
            self,
            collection_name: str,
            query_vector: List[float],
            limit: int = 3,
            score_threshold: float = 0.5
    ):
        """Search for similar vectors in the collection"""
        try:
            if not self.client or not self.connected:
                logger.error("❌ Qdrant client is not initialized. Cannot perform search.")
                return []

            try:
                results = self.client.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    score_threshold=score_threshold # Minimum similarity score to consider
                )
            except AttributeError:
                results = self.client.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=limit
                )

            return [
                {
                    "id": r.id,
                    "score": r.score,
                    "metadata": r.payload or {}
                }
                for r in results
            ]
                
        except Exception as e:
            logger.error(f"❌ Failed to search similar vectors in Qdrant: {type(e).__name__}")
            return []
        
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

            if not self.client:
                logger.error("❌ Qdrant client is not initialized. Cannot add point.")
                return False
            
            # Ensure collection exists
            self.create_collection(collection_name=collection_name, vector_size=len(vector))
            logger.info(f"✅ Adding point '{point_id}' to collection '{collection_name}' with metadata keys: {list(metadata.keys())}")
            
            point = models.PointStruct(
                id=str(point_id),
                vector=vector,
                payload=metadata
            )

            self.client.upsert(
                collection_name=collection_name,
                points=[point],
                wait=True # Wait for the operation to complete before returning
            )
            logger.debug(f"✅ Added point '{point_id}' to collection '{collection_name}' with metadata: {metadata}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to add point: {type(e).__name__}")
            return False

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection (use with caution)"""
        try:
            if not self.client:
                logger.error("❌ Qdrant client not initialized")
                return False
            
            self.client.delete_collection(collection_name)
            logger.info(f"✅ Deleted collection '{collection_name}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete collection: {type(e).__name__}")
            return False

    def get_collection_info(self, collection_name: str) -> Optional[Dict]:
        """Get collection information and stats"""
        try:
            if not self.client:
                return None
            
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "vector_size": info.config.params.vectors.size,
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to get collection info: {type(e).__name__}")
            return None

# Singleton instance for application-wide use
qdrant_vector_db = QdrantVectorDB()