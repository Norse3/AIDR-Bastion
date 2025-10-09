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

    async def run(self, prompt: str) -> PipelineResult | None:
        """
        Validates input text using the active client.

        Delegates the validation of input text to the currently active client.
        Returns None if no client is available.

        Args:
            prompt (str): Text prompt to analyze

        Returns:
            PipelineResult | None: Result of text validation or None if no client available
        """
        if not self._active_client:
            bastion_logger.warning("No active LLM client available for text validation")
            return None

        try:
            return await self._active_client.validate_input_text(prompt=prompt)
        except Exception as e:
            bastion_logger.error(f"Error during validation of input text with {self._active_client_id}: {e}")
            return None


llm_manager = LLMManager()
