from app.core.enums import ActionStatus
from app.core.manager import BaseManager
from app.managers.similarity.clients import ALL_CLIENTS_MAP
from app.managers.similarity.clients.base import BaseSearchClient
from app.models.pipeline import PipelineResult
from app.modules.logger import bastion_logger
from app.core.enums import ManagerNames
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

    _identifier: ManagerNames = ManagerNames.similarity
    description = "Manager class for similarity search operations using vector embeddings in database."

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

    def __str__(self) -> str:
        return "Similarity Manager"

    def _check_connections(self) -> None:
        """
        Checks connections for all initialized clients.
        Connection checks are deferred until the first async operation.
        """
        import asyncio
        bastion_logger.debug("Checking connections for all initialized clients")
        loop = asyncio.get_event_loop()
        for client in self._clients_map.values():
            try:
                loop.create_task(client.check_connection())
            except Exception as e:
                bastion_logger.error(f"Failed to check connection for {client}: {e}")
        bastion_logger.debug("Connection checks deferred until first async operation")

    async def run(self, text: str) -> PipelineResult:
        """
        Searches for similar documents using the active client.

        Delegates the similarity search to the currently active client.
        Returns an empty list if no client is available.

        Args:
            text (str): Text prompt to analyze for similar content

        Returns:
            PipelineResult: Analysis result with triggered rules and status
        """
        if not self._active_client:
            msg = "No active search client available for similarity search"
            bastion_logger.warning(msg)
            return PipelineResult(
                name=str(self),
                triggered_rules=[],
                status=ActionStatus.ERROR,
                details=msg,
            )

        try:
            # Check connection before running
            await self._active_client.check_connection()
            return await self._active_client.run(text=text)
        except Exception as e:
            msg = f"Error during similarity search with {self._active_client_id}: {e}"
            bastion_logger.error(msg)
            return PipelineResult(
                name=str(self),
                triggered_rules=[],
                status=ActionStatus.ERROR,
                details=msg,
            )

    async def close_connections(self) -> None:
        """
        Closes connections for all available clients.
        """
        for client in self._clients_map.values():
            await client.close()
