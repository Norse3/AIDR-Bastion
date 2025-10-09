from typing import Any, Dict, Optional

from elasticsearch import (
    AsyncElasticsearch,
    ConnectionError,
    ElasticsearchException,
    RequestError,
)

from app.core.exceptions import ConfigurationException
from app.managers.similarity.clients.base import BaseSearchClient
from app.modules.logger import bastion_logger
from settings import get_settings


class AsyncElasticsearchClient(BaseSearchClient):
    """
    Asynchronous client for working with Elasticsearch.

    This class provides functionality for connecting to Elasticsearch, executing search queries
    and working with vectors for finding similar documents. Supports automatic reconnection
    and error handling with detailed logging.

    Attributes:
        _client (AsyncElasticsearch): Asynchronous Elasticsearch client
        _es_settings (ElasticsearchSettings): Elasticsearch connection settings
    """

    _client: AsyncElasticsearch
    _identifier: str = "elasticsearch"

    def __init__(self) -> None:
        """
        Initializes Elasticsearch client with connection settings.

        Args:
            es_settings (ElasticsearchSettings): Settings for connecting to Elasticsearch
            similarity_prompt_index (str): Index name for searching similar prompts
        """
        settings = get_settings()
        if not settings.ES:
            raise Exception("Elasticsearch settings are not specified in environment variables")
        self._es_settings = settings.ES

        super().__init__(settings.SIMILARITY_PROMPT_INDEX)

        self._client = AsyncElasticsearch(
            hosts=[{"host": self._es_settings.host, "port": self._es_settings.port}],
            scheme=self._es_settings.scheme,
            http_auth=(self._es_settings.user, self._es_settings.password),
            use_ssl=True,
            verify_certs=False,
            ssl_show_warn=False,
            retry_on_status=(500, 502, 503, 504),
            retry_on_timeout=True,
            timeout=30,
            maxsize=self._es_settings.pool_size,
            max_retries=3,
        )

    def __str__(self) -> str:
        return "Elasticsearch Client"

    @property
    def client(self) -> AsyncElasticsearch:
        """
        Returns current Elasticsearch client.

        Returns:
            AsyncElasticsearch: Asynchronous Elasticsearch client

        Raises:
            AttributeError: If client is not initialized
        """
        return self._client

    async def check_connection(self) -> None:
        """
        Establishes connection with Elasticsearch server.

        Creates asynchronous connection to Elasticsearch, configures connection parameters
        and checks server availability. Logs errors if connection fails.

        Raises:
            Exception: On failed connection or Elasticsearch error
        """
        if not self._es_settings:
            return
        try:
            is_connected = await self._client.ping()
            if not is_connected:
                raise Exception("Failed to connect to Elasticsearch. Ping failed.")
            if not await self._client.indices.exists(index=self.similarity_prompt_index):
                raise Exception(f"Index `{self.similarity_prompt_index}` does not exist.")
        except Exception as e:
            raise ConfigurationException(f"{self} validation failed. Error: {str(e)}")

    async def close(self) -> None:
        """
        Closes connection with Elasticsearch server.

        Closes connection pool and cleans up client resources. Logs errors
        if connection closing fails.

        Raises:
            Exception: On connection closing error
        """
        try:
            if self._client:
                await self._client.close()
                self._client = None
        except ElasticsearchException as e:
            error_msg = f"Failed to close pool of connections to Elasticsearch. Error: {e}"
            bastion_logger.exception(f"[{self._es_settings.host}] {error_msg}")

    async def _search(self, index: str, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Executes search query to Elasticsearch.

        Private method for executing search queries to specified index.
        Handles connection and query errors with detailed logging.

        Args:
            index (str): Index name for search
            body (Dict[str, Any]): Search query body

        Returns:
            Optional[Dict[str, Any]]: Search query result from Elasticsearch or None on error

        Raises:
            Exception: On connection error or invalid query
        """
        try:
            return await self._client.search(index=index, body=body)
        except ConnectionError as e:
            error_msg = f"Failed to establish connection with Elasticsearch. Error: {e}"
            bastion_logger.error(f"[{self._es_settings.host}][{index}] {error_msg}")
            return None
        except RequestError as e:
            error_msg = f"Elasticsearch Response Error: Bad Request. Error: {e}"
            bastion_logger.exception(f"[{self._es_settings.host}] {error_msg}")
            return None
        except Exception as e:
            error_msg = f"Failed to execute search query. Error: {e}"
            bastion_logger.exception(f"[{self._es_settings.host}][{index}] {error_msg}")
            return None

    async def _index_exists(self, index: str) -> bool:
        """
        Checks if index exists in Elasticsearch.

        Args:
            index (str): Index name

        Returns:
            bool: True if index exists, False otherwise
        """
        try:
            return await self._client.indices.exists(index=index)
        except Exception as e:
            bastion_logger.error(f"[{self._es_settings.host}][{index}] Failed to check index existence: {e}")
            return False

    async def _ping(self) -> bool:
        """
        Performs ping to Elasticsearch.

        Returns:
            bool: True if ping is successful, False otherwise
        """
        try:
            return await self._client.ping()
        except Exception as e:
            bastion_logger.error(f"[{self._es_settings.host}] Ping failed: {e}")
            return False
