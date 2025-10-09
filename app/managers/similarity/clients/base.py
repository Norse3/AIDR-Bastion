import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.core.exceptions import ConfigurationException
from app.core.enums import RuleAction
from app.models.pipeline import PipelineResult, TriggeredRuleData
from app.modules.logger import bastion_logger
from app.utils import text_embedding, split_text_into_sentences
from settings import get_settings


settings = get_settings()


class BaseSearchClient(ABC):
    """
    Base class for working with search systems (Elasticsearch/OpenSearch).

    This class contains common functionality for connecting to search systems,
    executing search queries and working with vectors for finding similar documents.
    Supports automatic reconnection and error handling with detailed logging.

    Attributes:
        similarity_prompt_index (str): Index name for searching similar prompts
        _search_settings (BaseSearchSettings): Search system connection settings
    """

    _identifier: str | None = None

    def __init__(self, similarity_prompt_index: str, search_settings: Any) -> None:
        """
        Initializes search system client.

        Args:
            similarity_prompt_index (str): Index name for searching similar prompts
            settings (BaseSearchSettings): Search system connection settings
        """
        self.similarity_prompt_index = similarity_prompt_index
        self._search_settings = search_settings
        self.notify_threshold = settings.SIMILARITY_NOTIFY_THRESHOLD
        self.block_threshold = settings.SIMILARITY_BLOCK_THRESHOLD
        self._client = self._initialize_client()

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
    def client(self) -> Any:
        """
        Returns current search system client.

        Returns:
            Any: Search system client
        """
        return self._client

    @abstractmethod
    def _initialize_client(self) -> Any:
        """
        Initializes the search system client with specific configuration.

        Returns:
            Any: Initialized search system client
        """
        pass

    async def check_connection(self) -> None:
        """
        Establishes connection with search system server.

        Creates asynchronous connection to search system, configures connection parameters
        and checks server availability. Logs errors if connection fails.

        Raises:
            Exception: On failed connection or search system error
        """
        if not self._search_settings:
            return
        try:
            is_connected = await self._ping()
            if not is_connected:
                raise Exception(f"Failed to connect to {self}. Ping failed.")
            if not await self._index_exists(self.similarity_prompt_index):
                raise Exception(f"Index `{self.similarity_prompt_index}` does not exist.")
        except Exception as e:
            raise ConfigurationException(f"{self} validation failed. Error: {str(e)}")

    async def close(self) -> None:
        """
        Closes connection with search system server.

        Closes connection pool and cleans up client resources. Logs errors
        if connection closing fails.

        Raises:
            Exception: On connection closing error
        """
        try:
            if self._client:
                await self._client.close()
                self._client = None
        except Exception as e:
            error_msg = f"Failed to close pool of connections to {self}. Error: {e}"
            bastion_logger.exception(f"[{self._search_settings.host}] {error_msg}")

    async def _search(self, index: str, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Executes search query to search system.

        Private method for executing search queries to specified index.
        Handles connection and query errors with detailed logging.

        Args:
            index (str): Index name for search
            body (Dict[str, Any]): Search query body

        Returns:
            Optional[Dict[str, Any]]: Search query result from search system or None on error

        Raises:
            Exception: On connection error or invalid query
        """
        try:
            return await self._client.search(index=index, body=body)
        except Exception as e:
            if "ConnectionError" in str(type(e)):
                error_msg = f"Failed to establish connection with {self}. Error: {e}"
                bastion_logger.error(f"[{self._search_settings.host}][{index}] {error_msg}")
            elif "RequestError" in str(type(e)):
                error_msg = f"{self} Response Error: Bad Request. Error: {e}"
                bastion_logger.exception(f"[{self._search_settings.host}] {error_msg}")
            else:
                error_msg = f"Failed to execute search query. Error: {e}"
                bastion_logger.exception(f"[{self._search_settings.host}][{index}] {error_msg}")
            return None

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
        raise NotImplementedError("Subclasses must implement this method")

    async def _index_exists(self, index: str) -> bool:
        """
        Checks if index exists.

        Args:
            index (str): Index name

        Returns:
            bool: True if index exists, False otherwise
        """
        try:
            return await self._client.indices.exists(index=index)
        except Exception as e:
            bastion_logger.error(f"[{self._search_settings.host}][{index}] Failed to check index existence: {e}")
            return False

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

    async def _ping(self) -> bool:
        """
        Performs ping to search system.

        Returns:
            bool: True if ping is successful, False otherwise
        """
        try:
            return await self._client.ping()
        except Exception as e:
            bastion_logger.error(f"[{self._search_settings.host}] Ping failed: {e}")
            return False

    async def prepare_triggered_rules(self, similar_documents: list[dict]) -> list[TriggeredRuleData]:
        return [
            TriggeredRuleData(
                action=doc["action"], id=doc["doc_id"], name=doc["name"], details=doc["details"], body=doc["body"]
            )
            for doc in similar_documents
        ]


class BaseSearchClientMethods(BaseSearchClient):
    """
    Base class for search client methods.
    """

    def __split_prompt_into_sentences(self, prompt: str) -> list[str]:
        """
        Split prompt into sentences and return them as a list.

        Args:
            prompt (str): Text prompt to split

        Returns:
            list[str]: List of sentences from the prompt
        """
        return split_text_into_sentences(prompt)

    def _get_action(self, score: float) -> RuleAction:
        """
        Determines action based on similarity score.

        Compares the similarity score against configured thresholds
        to determine whether to block or notify.

        Args:
            score (float): Similarity score from vector search

        Returns:
            RuleAction: BLOCK if score exceeds block threshold, otherwise NOTIFY
        """
        if score >= self.block_threshold:
            return RuleAction.BLOCK
        return RuleAction.NOTIFY

    async def __search_similar_documents(self, chunk: str) -> list[dict]:
        """
        Search for similar documents using vector embeddings.

        Converts text chunk to vector embedding and searches OpenSearch
        for similar documents. Filters results by similarity threshold
        and formats them for further processing.

        Args:
            chunk (str): Text chunk to search for similar content

        Returns:
            list[dict]: List of similar documents with metadata and scores
        """
        vector = text_embedding(chunk)
        similar_documents = await self.search_similar_documents(vector)
        return [
            {
                "action": self._get_action(doc["_score"]),
                "doc_id": doc["_source"].get("id"),
                "name": doc["_source"].get("category"),
                "details": doc["_source"]["details"],
                "body": doc["_source"]["text"],
                "score": doc["_score"],
            }
            for doc in similar_documents
            if doc["_score"] > self.notify_threshold
        ]

    async def run(self, text: str) -> PipelineResult:
        """
        Analyzes prompt for similar content using vector similarity search.

        Splits the prompt into sentences, processes them in batches,
        and searches for similar documents using vector embeddings.
        Returns analysis results with triggered rules for similar content.

        Args:
            text (str): Text prompt to analyze for similar content

        Returns:
            PipelineResult: Analysis result with triggered rules and status
        """
        similar_documents = []
        chunks = self.__split_prompt_into_sentences(text)
        bastion_logger.info(f"Analyzing for {len(chunks)} sentences")

        batch_size = 5
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            tasks = [self.__search_similar_documents(chunk) for chunk in batch]
            batch_results = await asyncio.gather(*tasks)
            for result in batch_results:
                similar_documents.extend(result)
        triggered_rules = await self.prepare_triggered_rules(similar_documents)
        bastion_logger.info(f"Found {len(triggered_rules)} similar documents")
        return PipelineResult(
            name=str(self), status=self._pipeline_status(triggered_rules), triggered_rules=triggered_rules
        )
