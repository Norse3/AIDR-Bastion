from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.modules.logger import bastion_logger


class BaseSearchClient(ABC):
    """
    Base class for working with search systems (Elasticsearch/OpenSearch).

    This class contains common functionality for connecting to search systems,
    executing search queries and working with vectors for finding similar documents.
    Supports automatic reconnection and error handling with detailed logging.

    Attributes:
        similarity_prompt_index (str): Index name for searching similar prompts
    """

    _identifier: str | None = None

    def __init__(self, similarity_prompt_index: str) -> None:
        """
        Initializes search system client.

        Args:
            similarity_prompt_index (str): Index name for searching similar prompts
        """
        self.similarity_prompt_index = similarity_prompt_index

    def __str__(self) -> str:
        """
        String representation of the client.

        Returns:
            str: Class name of the client
        """
        return self.__class__.__name__

    def __repr__(self) -> str:
        """
        String representation of the client.

        Returns:
            str: Class name of the client
        """
        return self.__str__()

    @property
    @abstractmethod
    def client(self) -> Any:
        """
        Returns current search system client.

        Returns:
            Any: Search system client
        """
        pass

    @abstractmethod
    async def check_connection(self) -> None:
        """
        Establishes connection with search system server.

        Raises:
            Exception: On failed connection or search system error
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Closes connection with search system server.

        Raises:
            Exception: On connection closing error
        """
        pass

    @abstractmethod
    async def _search(self, index: str, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Executes search query to search system.

        Args:
            index (str): Index name for search
            body (Dict[str, Any]): Search query body

        Returns:
            Optional[Dict[str, Any]]: Search query result or None on error
        """
        pass

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

    @abstractmethod
    async def _index_exists(self, index: str) -> bool:
        """
        Checks if index exists.

        Args:
            index (str): Index name

        Returns:
            bool: True if index exists, False otherwise
        """
        pass

    async def test_connection(self) -> bool:
        """
        Tests connection with search system and basic functionality.

        Returns:
            bool: True if connection is working, False otherwise
        """
        try:
            # Test basic ping
            if not await self._ping():
                return False

            # Test index existence
            if not await self._index_exists(self.similarity_prompt_index):
                bastion_logger.warning(f"[{self.similarity_prompt_index}] Index does not exist for testing")
                return False

            # Test simple query
            test_body = {"size": 1, "query": {"match_all": {}}}

            resp = await self._search(index=self.similarity_prompt_index, body=test_body)
            if resp:
                bastion_logger.info(f"[{self.similarity_prompt_index}] Connection test successful")
                return True
            else:
                bastion_logger.error(f"[{self.similarity_prompt_index}] Connection test failed - no response")
                return False

        except Exception as e:
            bastion_logger.error(f"[{self.similarity_prompt_index}] Connection test failed: {e}")
            return False

    @abstractmethod
    async def _ping(self) -> bool:
        """
        Performs ping to search system.

        Returns:
            bool: True if ping is successful, False otherwise
        """
        pass
