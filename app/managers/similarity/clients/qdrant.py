from typing import Any, Dict, List

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, ScoredPoint

from app.managers.similarity.clients.base import BaseSearchClientMethods
from app.models.pipeline import TriggeredRuleData
from app.modules.logger import bastion_logger
from app.core.enums import SimilarityClientNames
from settings import get_settings


class AsyncQdrantClientWrapper(BaseSearchClientMethods):
    """
    Asynchronous client for working with Qdrant vector database.

    Qdrant is a specialized vector search engine optimized for similarity search
    and filtering. This client provides high-performance vector similarity search
    with advanced filtering capabilities.

    Key features:
    - Native vector search with HNSW algorithm
    - Efficient filtering by payload fields
    - Optimized memory usage
    - Simple and clean API
    """

    _identifier: SimilarityClientNames = SimilarityClientNames.qdrant
    description = "Qdrant-based client for high-performance similarity search operations using vector embeddings."

    def __init__(self) -> None:
        """
        Initializes Qdrant client with connection settings.
        """
        settings = get_settings()
        if not settings.QDRANT:
            raise Exception("Qdrant settings are not specified in environment variables")

        super().__init__(settings.SIMILARITY_PROMPT_INDEX, settings.QDRANT)

    def __str__(self) -> str:
        return "Qdrant Client"

    def _initialize_client(self) -> AsyncQdrantClient:
        """
        Initializes Qdrant client with specific configuration.

        Returns:
            AsyncQdrantClient: Initialized Qdrant client
        """
        return AsyncQdrantClient(**self._search_settings.get_client_config())

    async def _ping(self) -> bool:
        """
        Performs health check for Qdrant service.

        Returns:
            bool: True if service is healthy, False otherwise
        """
        try:
            health = await self._client.health()
            return health is not None
        except Exception as e:
            bastion_logger.error(f"[{self._search_settings.host}] Ping failed: {e}")
            return False

    async def _index_exists(self, collection_name: str) -> bool:
        """
        Checks if collection exists in Qdrant.

        Args:
            collection_name (str): Name of the collection to check

        Returns:
            bool: True if collection exists, False otherwise
        """
        try:
            collections = await self._client.get_collections()
            return any(col.name == collection_name for col in collections.collections)
        except Exception as e:
            bastion_logger.error(f"[{self._search_settings.host}][{collection_name}] Failed to check collection existence: {e}")
            return False

    async def search_similar_documents(self, vector: List[float]) -> List[Dict[str, Any]]:
        """
        Searches for similar documents by vector using cosine similarity.

        Performs high-performance vector similarity search using Qdrant's
        optimized HNSW algorithm. Returns up to 5 most similar documents
        with optional filtering by payload fields.

        Args:
            vector (List[float]): Vector for searching similar documents

        Returns:
            List[Dict[str, Any]]: List of similar documents with metadata and scores
        """
        if not vector or not isinstance(vector, list) or len(vector) == 0:
            bastion_logger.warning(f"[{self.similarity_prompt_index}] Invalid vector provided for similarity search")
            return []

        # Check if vector has expected dimensions (typically 768 for many embedding models)
        if len(vector) != 768:
            bastion_logger.warning(
                f"[{self.similarity_prompt_index}] Vector dimension mismatch: expected 768, got {len(vector)}"
            )

        # Log the query for debugging
        bastion_logger.debug(
            f"[{self.similarity_prompt_index}] Executing similarity search with vector length: {len(vector)}"
        )

        try:
            # Check if collection exists before searching
            if not await self._index_exists(self.similarity_prompt_index):
                bastion_logger.warning(f"[{self.similarity_prompt_index}] Collection does not exist")
                return []
        except Exception as e:
            bastion_logger.error(f"[{self.similarity_prompt_index}] Failed to check collection existence: {e}")
            return []

        try:
            # Perform vector search with score threshold
            results: List[ScoredPoint] = await self._client.search(
                collection_name=self.similarity_prompt_index,
                query_vector=vector,
                limit=5,
                score_threshold=self.notify_threshold,  # Built-in threshold filtering
            )

            # Deduplicate by category - keep only the best match per category
            documents = {}
            for point in results:
                category = point.payload.get("category")
                if category not in documents:
                    documents[category] = {
                        "_score": point.score,
                        "_source": {
                            "id": point.payload.get("id"),
                            "category": category,
                            "details": point.payload.get("details", ""),
                            "text": point.payload.get("text", ""),
                        }
                    }

            return list(documents.values())

        except Exception as e:
            bastion_logger.error(f"[{self.similarity_prompt_index}] Failed to search similar documents: {e}")
            return []

    async def index_create(self) -> bool:
        """
        Creates a new collection in Qdrant with vector configuration.

        Returns:
            bool: True if collection was created successfully, False otherwise
        """
        try:
            await self._client.create_collection(
                collection_name=self.similarity_prompt_index,
                vectors_config=VectorParams(
                    size=768,  # Vector dimension
                    distance=Distance.COSINE,  # Cosine similarity
                ),
            )
            bastion_logger.info(f"[{self}][{self._search_settings.host}][{self.similarity_prompt_index}] Collection created successfully")
            return True
        except Exception as e:
            bastion_logger.error(f"[{self}][{self._search_settings.host}][{self.similarity_prompt_index}] Failed to create collection: {e}")
            return False

    async def index(self, body: Dict[str, Any]) -> bool:
        """
        Indexes a single document into Qdrant collection.

        Args:
            body (Dict[str, Any]): Document to index with keys: id, vector, text, category, details

        Returns:
            bool: True if indexing was successful, False otherwise
        """
        try:
            point = PointStruct(
                id=body.get("id"),
                vector=body.get("vector"),
                payload={
                    "id": body.get("id"),
                    "text": body.get("text"),
                    "category": body.get("category", ""),
                    "details": body.get("details", ""),
                }
            )

            await self._client.upsert(
                collection_name=self.similarity_prompt_index,
                points=[point]
            )

            bastion_logger.debug(f"[{self.similarity_prompt_index}] Indexed document: {body.get('id')}")
            return True

        except Exception as e:
            bastion_logger.error(f"[{self}][{self._search_settings.host}][{self.similarity_prompt_index}] Failed to index document: {e}")
            return False

    async def prepare_triggered_rules(self, similar_documents: list[dict]) -> list[TriggeredRuleData]:
        """
        Prepare rules with deduplication by doc_id.

        For identical documents, preference is given to those with higher score.
        Converts similar documents to TriggeredRuleData objects.

        Args:
            similar_documents (list[dict]): List of documents with search results

        Returns:
            list[TriggeredRuleData]: List of unique TriggeredRuleData objects
        """
        deduplicated_docs = {}
        for doc in similar_documents:
            doc_id = doc["doc_id"]
            if doc_id not in deduplicated_docs or doc["score"] > deduplicated_docs[doc_id]["score"]:
                deduplicated_docs[doc_id] = doc

        return [
            TriggeredRuleData(
                action=doc["action"],
                id=doc["doc_id"],
                name=doc["name"],
                details=doc["details"],
                body=doc["body"]
            )
            for doc in deduplicated_docs.values()
        ]

    async def close(self) -> None:
        """
        Closes connection with Qdrant server.

        Properly closes the client connection and cleans up resources.
        """
        try:
            if self._client:
                await self._client.close()
                self._client = None
                bastion_logger.debug(f"[{self}] Connection closed successfully")
        except Exception as e:
            error_msg = f"Failed to close connection to {self}. Error: {e}"
            bastion_logger.exception(f"[{self._search_settings.host}] {error_msg}")
