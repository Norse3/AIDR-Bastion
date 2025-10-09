from typing import Any, Dict, List
from elasticsearch import AsyncElasticsearch

from app.managers.similarity.clients.base import BaseSearchClientMethods
from app.models.pipeline import TriggeredRuleData
from app.modules.logger import bastion_logger
from settings import get_settings


class AsyncElasticsearchClient(BaseSearchClientMethods):
    """
    Asynchronous client for working with Elasticsearch.

    This class provides functionality for connecting to Elasticsearch, executing search queries
    and working with vectors for finding similar documents. Supports automatic reconnection
    and error handling with detailed logging.
    """

    _identifier: str = "elasticsearch"

    def __init__(self) -> None:
        """
        Initializes Elasticsearch client with connection settings.
        """
        settings = get_settings()
        if not settings.ES:
            raise Exception("Elasticsearch settings are not specified in environment variables")

        super().__init__(settings.SIMILARITY_PROMPT_INDEX, settings.ES)

    def __str__(self) -> str:
        return "Elasticsearch Client"

    def _initialize_client(self) -> AsyncElasticsearch:
        """
        Initializes Elasticsearch client with specific configuration.

        Returns:
            AsyncElasticsearch: Initialized Elasticsearch client
        """
        return AsyncElasticsearch(**self._settings.get_client_config())

    async def search_similar_documents(self, vector: List[float]) -> List[Dict[str, Any]]:
        """
        Searches for similar documents by vector using cosine similarity.

        Performs search for documents similar to given vector using
        cosine similarity. Returns up to 5 most similar documents, grouping
        them by categories to avoid duplicates.

        Args:
            vector (List[float]): Vector for searching similar documents

        Returns:
            List[Dict[str, Any]]: List of similar documents, grouped by categories.
                                 Each document contains metadata and source data.
        """
        if not vector or not isinstance(vector, list) or len(vector) == 0:
            bastion_logger.warning(f"[{self.similarity_prompt_index}] Invalid vector provided for similarity search")
            return []

        # Check if vector has expected dimensions (typically 768 for many embedding models)
        if len(vector) != 768:
            bastion_logger.warning(
                f"[{self.similarity_prompt_index}] Vector dimension mismatch: expected 768, got {len(vector)}"
            )

        # Use KNN query for vector similarity search
        body = {"size": 5, "query": {"knn": {"vector": {"vector": vector, "k": 5}}}}

        # Log the query for debugging
        bastion_logger.debug(
            f"[{self.similarity_prompt_index}] Executing similarity search with vector length: {len(vector)}"
        )
        bastion_logger.debug(f"[{self.similarity_prompt_index}] Query body: {body}")

        try:
            # Check if index exists before searching
            if not await self._index_exists(self.similarity_prompt_index):
                bastion_logger.warning(f"[{self.similarity_prompt_index}] Index does not exist")
                return []
        except Exception as e:
            bastion_logger.error(f"[{self.similarity_prompt_index}] Failed to check index existence: {e}")
            return []

        resp = await self._search(index=self.similarity_prompt_index, body=body)
        if resp:
            documents = {}
            for hit in resp.get("hits", {}).get("hits", []):
                if hit["_source"]["category"] not in documents:
                    documents[hit["_source"]["category"]] = hit
            return list(documents.values())

        # Fallback: try simpler KNN query if the main one failed
        bastion_logger.warning(f"[{self.similarity_prompt_index}] Main KNN query failed, trying fallback")
        fallback_body = {"size": 5, "query": {"knn": {"vector": {"vector": vector, "k": 3}}}}

        fallback_resp = await self._search(index=self.similarity_prompt_index, body=fallback_body)
        if fallback_resp:
            documents = {}
            for hit in fallback_resp.get("hits", {}).get("hits", []):
                if hit["_source"]["category"] not in documents:
                    documents[hit["_source"]["category"]] = hit
            return list(documents.values())

        bastion_logger.error(f"[{self.similarity_prompt_index}] Failed to search similar documents - no response")
        return []

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
                action=doc["action"], id=doc["doc_id"], name=doc["name"], details=doc["details"], body=doc["body"]
            )
            for doc in deduplicated_docs.values()
        ]
