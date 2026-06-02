import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

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
    Vector database client for semantic search and embeddings.
    Used for route recommendations, driver matching, chat context.
    """

    def __init__(self):
        self.client = None
        self.embedding_model = None
        self.vector_size = 384
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

            # Load sentence transformer model for embeddings
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info(f"✅ Connected to Qdrant at {qdrant_host}")
            logger.info(f"✅ Loaded embedding model: all-MiniLM-L6-v2 ({self.vector_size} dimensions)")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Qdrant client: {e}")
            raise

    def create_collection(self, collection_name: str):
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
                    size=self.vector_size,
                    distance=Distance.COSINE # Cosine similarity for semantic search
                )
            )
            logger.info(f"✅ Collection '{collection_name}' created successfully.")

        except Exception as e:
            logger.error(f"❌ Failed to create Qdrant collections: {e}")
            raise

    def embed_text(self, text: str) -> List[float]:
        """Convert text to embedding vector using the loaded model"""
        try:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"❌ Failed to embed text: {e}")
            raise

    def add_point(self, collection_name: str, point_id: str, text: str, metadata: Dict[str, Any]):
        """Add a vector point to the collection"""
        try:
            vector = self.embed_text(text)

            point = PointStruct(
                id=point_id,
                vector=vector,
                payload=metadata # Store metadata for filtering and retrieval
            )

            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            logger.debug(f"✅ Added point '{point_id}' to collection '{collection_name}' with metadata: {metadata}")

        except Exception as e:
            logger.error(f"❌ Failed to add point to Qdrant: {e}")
            raise

    
    def search_similar(self, collection_name: str, text: str, limit: int = 5) -> List[Dict]:
        """Search for similar vectors in the collection"""
        try:
            query_vector = self.embed_text(text)

            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=0.5 # Minimum similarity score to consider
            )

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

# Singleton instance for application-wide use
qdrant_vector_db = QdrantVectorDB()