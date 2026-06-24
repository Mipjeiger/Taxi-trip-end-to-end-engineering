import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
from qdrant_client.http import models
from qdrant_client import QdrantClient
from app.core.config import settings
from qdrant_client.models import Distance, VectorParams
import json

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR.parent / '.env'
logger.info(f"✅ Loaded environment variables from: {ENV_PATH}")

if not ENV_PATH.exists():
    ENV_PATH = BASE_DIR / '.env'
    logging.debug(f"⚠️ .env file not found at {ENV_PATH}, trying fallback location: {ENV_PATH}")

load_dotenv(dotenv_path=ENV_PATH)

# ================================================================
# Qdrant Client for Vector Search and Similarity
# ================================================================
class QdrantVectorDB:
    """
    Pure Qdrant client for Qdrant Cloud.

    No embedding model
    No sentence transformer
    No torch

    Accept vectors generated elsewhere
    """

    def __init__(self):
        self.client = None
        self.connected = False
        self.collection_configs = {}  # Cache collection configs
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Qdrant client connection to Qdrant Cloud"""
        try:
            # Use Qdrant Cloud
            if settings.QDRANT_URL and settings.QDRANT_URL.strip():
                # Remove trailing slashes
                url = settings.QDRANT_URL.rstrip('/')
                
                logger.info(f"🔗 Connecting to Qdrant Cloud: {url}")
                
                self.client = QdrantClient(
                    url=url,
                    api_key=settings.QDRANT_API_KEY,
                    timeout=60,
                    prefer_grpc=False  # Use HTTP for cloud
                )
            else:
                logger.warning("⚠️ QDRANT_URL not configured. Qdrant features disabled.")
                self.connected = False
                self.client = None
                return

            # Test connection
            self.client.get_collections()
            self.connected = True
            logger.info("✅ Successfully connected to Qdrant Cloud.")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Qdrant client: {e}")
            self.connected = False
            self.client = None

    def create_collection(self, collection_name: str, vector_size: int = 384):
        """Create a new collection for storing embeddings with proper error handling"""
        try:
            if not self.client or not self.connected:
                logger.error("❌ Qdrant client is not initialized. Cannot create collection.")
                return False

            # Get existing collections
            collections = self.client.get_collections().collections
            existing_names = [col.name for col in collections]

            if collection_name in existing_names:
                # Check vector size
                collection_info = self.client.get_collection(collection_name)
                existing_size = collection_info.config.params.vectors.size
                
                logger.info(f"📂 Collection '{collection_name}' exists with vector size: {existing_size}")

                if existing_size != vector_size:
                    logger.warning(f"⚠️ Vector dimension mismatch: existing={existing_size}, required={vector_size}")
                    logger.info(f"🗑️ Deleting and recreating collection '{collection_name}'...")
                    
                    # Delete old collection
                    self.client.delete_collection(collection_name=collection_name)
                    logger.info(f"✅ Deleted collection '{collection_name}'")
                    
                    # Create new collection
                    self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=models.VectorParams(
                            size=vector_size,
                            distance=models.Distance.COSINE
                        )
                    )
                    logger.info(f"✅ Created collection '{collection_name}' with size {vector_size}")
                else:
                    logger.info(f"✅ Collection '{collection_name}' already exists with correct dimensions")
                return True
            else:
                # Create new collection
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Created collection '{collection_name}' with size {vector_size}")
                return True

        except Exception as e:
            logger.error(f"❌ Failed to create collection: {e}")
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

            # Ensure collection exists
            self.create_collection(collection_name, len(query_vector))

            try:
                results = self.client.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=limit,
                    score_threshold=score_threshold
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
            logger.error(f"❌ Failed to search vectors in Qdrant: {e}")
            return []
        
    def add_point(
        self,
        collection_name: str,
        point_id: str,
        vector: List[float],
        metadata: Dict[str, Any]
    ):
        """
        Insert a vector point into Qdrant Cloud.
        """
        try:
            if not self.client or not self.connected:
                logger.error("❌ Qdrant client is not initialized. Cannot add point.")
                return False
            
            # Validate vector
            if not vector or len(vector) == 0:
                logger.error("❌ Empty vector provided")
                return False
            
            vector_size = len(vector)
            logger.info(f"📊 Adding point with vector size: {vector_size}")
            
            # Ensure collection exists with correct dimensions
            collection_created = self.create_collection(
                collection_name=collection_name, 
                vector_size=vector_size
            )
            
            if not collection_created:
                logger.error(f"❌ Failed to create/verify collection '{collection_name}'")
                return False
            
            # Create point
            point = models.PointStruct(
                id=str(point_id),
                vector=vector,
                payload=metadata
            )

            # Upsert with wait
            self.client.upsert(
                collection_name=collection_name,
                points=[point],
                wait=True
            )
            
            logger.info(f"✅ Added point '{point_id}' to collection '{collection_name}'")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to add point to Qdrant: {e}")
            
            # Try to get more details about the error
            try:
                # Check collection info
                collection_info = self.client.get_collection(collection_name)
                logger.info(f"📊 Collection info: size={collection_info.config.params.vectors.size}")
            except Exception as coll_err:
                logger.error(f"❌ Could not get collection info: {coll_err}")
            
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
            logger.error(f"❌ Failed to delete collection: {e}")
            return False

    def get_collection_info(self, collection_name: str) -> Optional[Dict]:
        """Get collection information and stats"""
        try:
            if not self.client:
                return None
            
            info = self.client.get_collection(collection_name)
            
            # Handle different qdrant-client versions
            vectors_count = getattr(info, "vectors_count", None)
            points_count = getattr(info, "points_count", None)

            if vectors_count is None and hasattr(info, 'segments'):
                vectors_count = sum(seg.vectors_count for seg in info.segments)
                points_count = sum(seg.points_count for seg in info.segments)

            # Get vector size
            vector_size = None
            if hasattr(info, "config") and hasattr(info.config, "params"):
                if hasattr(info.config.params, "vectors"):
                    vector_size = info.config.params.vectors.size

            return {
                "name": collection_name,
                "vectors_count": vectors_count,
                "points_count": points_count,
                "vector_size": vector_size,
                "status": "healthy"
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to get collection info: {e}")
            return None
    
    def health_check(self) -> Dict:
        """Check Qdrant Cloud health and connection"""
        try:
            if not self.client or not self.connected:
                return {"status": "disconnected", "connected": False}
            
            # Test connection
            collections = self.client.get_collections()
            return {
                "status": "healthy",
                "connected": True,
                "collections": [c.name for c in collections.collections],
                "url": settings.QDRANT_URL
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }

# Singleton instance for application-wide use
qdrant_vector_db = QdrantVectorDB()