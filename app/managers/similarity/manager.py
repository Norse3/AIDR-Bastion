from typing import Dict, List

from app.core.manager import BaseManager
from app.managers.similarity.clients import ALL_CLIENTS_MAP
from app.managers.similarity.clients.base import BaseSearchClient
from app.modules.logger import bastion_logger
from settings import get_settings

settings = get_settings()


class SimilarityManager(BaseManager[BaseSearchClient]):
    """
    Manager class for similarity search operations.

    This class manages connections to both OpenSearch and Elasticsearch clients,
    providing a unified interface for similarity search operations. It automatically
    selects the appropriate client based on available settings, with Elasticsearch
    being the default when both are available.

    Attributes:
        _clients_map (Dict[str, BaseSearchClient]): Mapping of client identifiers to client instances
        _active_client (Optional[BaseSearchClient]): Currently active client for operations
        _active_client_id (str): Identifier of the active client
    """

    def __init__(self) -> None:
        """
        Initializes SimilarityManager with available search clients.

        Creates instances of OpenSearch and Elasticsearch clients based on
        available settings. Sets the active client according to priority:
        1. Elasticsearch (if available)
        2. OpenSearch (if available)
        3. None (if neither available)
        """
        super().__init__(ALL_CLIENTS_MAP, "SIMILARITY_DEFAULT_CLIENT")
        self._check_connections()

    def _check_connections(self) -> None:
        """
        Checks connections for all initialized clients.
        """
        import asyncio

        for client in self._clients_map.values():
            try:
                asyncio.create_task(client.check_connection())
            except Exception as e:
                bastion_logger.error(f"Failed to check connection for {client}: {e}")

    async def run(self, vector: List[float]) -> List[Dict[str, any]]:
        """
        Searches for similar documents using the active client.

        Delegates the similarity search to the currently active client.
        Returns an empty list if no client is available.

        Args:
            vector (List[float]): Vector for searching similar documents

        Returns:
            List[Dict[str, any]]: List of similar documents found by the active client
        """
        if not self._active_client:
            bastion_logger.warning("No active search client available for similarity search")
            return []

        try:
            return await self._active_client.search_similar_documents(vector)
        except Exception as e:
            bastion_logger.error(f"Error during similarity search with {self._active_client_id}: {e}")
            return []

    async def close_connections(self) -> None:
        """
        Closes connections for all available clients.
        """
        for client in self._clients_map.values():
            await client.close()


similarity_manager = SimilarityManager()
