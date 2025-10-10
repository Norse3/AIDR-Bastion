from app.core.enums import ActionStatus, ManagerNames
from app.core.manager import BaseManager
from app.managers.llm.clients import ALL_CLIENTS_MAP
from app.managers.llm.clients.base import BaseLLMClient
from app.models.pipeline import PipelineResult
from app.modules.logger import bastion_logger
from settings import get_settings

settings = get_settings()


class LLMManager(BaseManager[BaseLLMClient]):
    """
    Manager class for similarity search operations.

    This class manages connections to different LLM clients,
    providing a unified interface for LLM operations. It automatically
    selects the appropriate client based on available settings, with OpenAI
    being the default when both are available.

    Attributes:
        _clients_map (Dict[str, BaseLLMClient]): Mapping of client identifiers to client instances
        _active_client (Optional[BaseSearchClient]): Currently active client for operations
        _active_client_id (str): Identifier of the active client
    """

    _identifier: ManagerNames = ManagerNames.llm
    description = "Manager class for LLM operations using AI language models."

    def __init__(self) -> None:
        """
        Initializes LLMManager with available LLM clients.

        Creates LLM clients based on available settings.
        Sets the active client according to priority:
        1. OpenAI (if available)
        2. Other LLM clients (if available)
        3. None (if neither available)
        """
        super().__init__(ALL_CLIENTS_MAP, "LLM_DEFAULT_CLIENT")

    def __str__(self) -> str:
        return "LLM Manager"

    async def _check_connections(self) -> None:
        """
        Checks connections for all initialized clients.
        Connection checks are deferred until the first async operation.
        """
        bastion_logger.debug("Checking connections for all initialized clients")
        for client in self._clients_map.values():
            try:
                status = await client.check_connection()
                if status:
                    client.enabled = True
                    bastion_logger.info(f"[{self}][{client}] Connection check successful")
                else:
                    bastion_logger.error(f"[{self}][{client}] Check connection failed")
            except Exception as e:
                bastion_logger.error(f"{str(e)}")

    async def run(self, text: str) -> PipelineResult:
        """
        Validates input text using the active client.

        Delegates the validation of input text to the currently active client.
        Returns PipelineResult with ERROR status if no client is available.

        Args:
            text (str): Text prompt to analyze

        Returns:
            PipelineResult: Result of text validation or ERROR status if no client available
        """
        if not self._active_client:
            msg = "No active LLM client available for text validation"
            bastion_logger.warning(msg)
            return PipelineResult(
                name=str(self),
                triggered_rules=[],
                status=ActionStatus.ERROR,
                details=msg,
            )

        try:
            return await self._active_client.run(text=text)
        except Exception as e:
            msg = f"Error during validation of input text with {self._active_client_id}: {e}"
            bastion_logger.error(msg)
            return PipelineResult(
                name=str(self),
                triggered_rules=[],
                status=ActionStatus.ERROR,
                details=msg,
            )
