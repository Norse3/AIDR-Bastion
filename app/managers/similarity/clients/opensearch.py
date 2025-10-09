from typing import Any, Dict, Optional

from opensearchpy import (
    AsyncOpenSearch,
    ConnectionError,
    OpenSearchException,
    RequestError,
)

from app.core.exceptions import ConfigurationException
from app.managers.similarity.clients.base import BaseSearchClient
from app.modules.logger import bastion_logger
from settings import OpenSearchSettings, get_settings


class AsyncOpenSearchClient(BaseSearchClient):
    """
    Asynchronous client for working with OpenSearch.

    This class provides functionality for connecting to OpenSearch, executing search queries
    and working with vectors for finding similar documents. Supports automatic reconnection
    and error handling with detailed logging.

    Attributes:
        _client (AsyncOpenSearch): Asynchronous OpenSearch client
        _os_settings (OpenSearchSettings): OpenSearch connection settings
    """

    _client: AsyncOpenSearch
    _identifier: str = "opensearch"

    def __init__(self, os_settings: OpenSearchSettings, similarity_prompt_index: str) -> None:
        """
        Initializes OpenSearch client with connection settings.

        Args:
            os_settings (OpenSearchSettings): Settings for connecting to OpenSearch
            similarity_prompt_index (str): Index name for searching similar prompts
        """
        settings = get_settings()
        if not settings.OS:
            raise Exception("OpenSearch settings are not specified in environment variables")
        self._os_settings = settings.OS
        super().__init__(similarity_prompt_index)

        self._client = AsyncOpenSearch(
            hosts=[{"host": self._os_settings.host, "port": self._os_settings.port}],
            scheme=self._os_settings.scheme,
            http_auth=(self._os_settings.user, self._os_settings.password),
            use_ssl=True,
            verify_certs=False,
            ssl_show_warn=False,
            retry_on_status=(500, 502, 503, 504),
            retry_on_timeout=True,
            timeout=30,
            pool_maxsize=self._os_settings.pool_size,
            max_retries=3,
        )

    def __str__(self) -> str:
        return "OpenSearch Client"

    @property
    def client(self) -> AsyncOpenSearch:
        """
        Returns current OpenSearch client.

        Returns:
            AsyncOpenSearch: Asynchronous OpenSearch client

        Raises:
            AttributeError: If client is not initialized
        """
        return self._client

    async def check_connection(self) -> None:
        """
        Establishes connection with OpenSearch server.

        Creates asynchronous connection to OpenSearch, configures connection parameters
        and checks server availability. Logs errors if connection fails.

        Raises:
            Exception: On failed connection or OpenSearch error
        """
        if not self._os_settings:
            return
        try:
            is_connected = await self._client.ping()
            if not is_connected:
                raise Exception("Failed to connect to OpenSearch. Ping failed.")
            if not await self._client.indices.exists(index=self.similarity_prompt_index):
                raise Exception(f"Index `{self.similarity_prompt_index}` does not exist.")
        except Exception as e:
            raise ConfigurationException(f"{self} validation failed. Error: {str(e)}")

    async def close(self) -> None:
        """
        Closes connection with OpenSearch server.

        Closes connection pool and cleans up client resources. Logs errors
        if connection closing fails.

        Raises:
            Exception: On connection closing error
        """
        try:
            if self._client:
                await self._client.close()
                self._client = None
        except OpenSearchException as e:
            error_msg = f"Failed to close pool of connections to OpenSearch. Error: {e}"
            bastion_logger.exception(f"[{self._os_settings.host}] {error_msg}")

    async def _search(self, index: str, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Executes search query to OpenSearch.

        Private method for executing search queries to specified index.
        Handles connection and query errors with detailed logging.

        Args:
            index (str): Index name for search
            body (Dict[str, Any]): Search query body

        Returns:
            Optional[Dict[str, Any]]: Search query result from OpenSearch or None on error

        Raises:
            Exception: On connection error or invalid query
        """
        try:
            return await self._client.search(index=index, body=body)
        except ConnectionError as e:
            error_msg = f"Failed to establish connection with OpenSearch. Error: {e}"
            bastion_logger.error(f"[{self._os_settings.host}][{index}] {error_msg}")
            return None
        except RequestError as e:
            error_msg = f"OpenSearch Response Error: Bad Request. Error: {e}"
            bastion_logger.exception(f"[{self._os_settings.host}] {error_msg}")
            return None
        except Exception as e:
            error_msg = f"Failed to execute search query. Error: {e}"
            bastion_logger.exception(f"[{self._os_settings.host}][{index}] {error_msg}")
            return None

    async def _index_exists(self, index: str) -> bool:
        """
        Checks if index exists in OpenSearch.

        Args:
            index (str): Index name

        Returns:
            bool: True if index exists, False otherwise
        """
        try:
            return await self._client.indices.exists(index=index)
        except Exception as e:
            bastion_logger.error(f"[{self._os_settings.host}][{index}] Failed to check index existence: {e}")
            return False

    async def _ping(self) -> bool:
        """
        Performs ping to OpenSearch.

        Returns:
            bool: True if ping is successful, False otherwise
        """
        try:
            return await self._client.ping()
        except Exception as e:
            bastion_logger.error(f"[{self._os_settings.host}] Ping failed: {e}")
            return False
