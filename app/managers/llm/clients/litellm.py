from typing import Any

# import ollama
import openai

from app.core.enums import ActionStatus, LLMClientNames
from app.core.exceptions import ConfigurationException
from app.managers.llm.clients.base import BaseLLMClient
from app.models.pipeline import PipelineResult
from app.modules.logger import bastion_logger
from settings import get_settings

settings = get_settings()


class AsyncLiteLLMClient(BaseLLMClient):
    """
    LiteLLM-based pipeline for analyzing prompts using locally hosted LLM models.

    This pipeline uses the LiteLLM router, sending requests to OpenRouter and/or Ollama, 
    to analyze prompts for potential issues, ethical concerns, or harmful content. 

    Attributes:
        # _client (ollama.AsyncClient): Official Ollama async client
        _identifier (LLMClientNames): Ollama identifier
        model (str): Model to use for analysis (e.g., llama3, mistral)
        SYSTEM_PROMPT (str): System prompt for AI analysis
    """

    # _client: ollama.AsyncClient
    _identifier: LLMClientNames = LLMClientNames.litellm
    description = "LiteLLM-based client for locally routed LLM models or Cloud-based models (via OpenRouter)."

    def __init__(self):
        """
        Initializes LiteLLM pipeline with API client and model configuration.

        Sets up an async client pointing to LiteLLM router server
        and configures the model for analysis.
        """
        super().__init__()
        self.client = None
        model = settings.LITELLM_MODEL
        self.model = model
        self.system_prompt = self._build_system_prompt()
        self.__load_client()

    def _get_additional_instructions(self) -> str:
        """
        Get Ollama-specific additional instructions.

        Returns:
            str: Additional instructions for Ollama models
        """
        return """### LiteLLM-Specific Instructions
- Provide concise and structured responses
- Always return valid JSON format as specified above
- Focus on accurate threat detection for local LLM deployments"""

    def __str__(self) -> str:
        return "LiteLLM Client"

    async def check_connection(self) -> None | Any:
        """
        Checks connection to LiteLLM Proxy Router.

        Raises:
            Exception: On failed connection or API error
        """
        try:
            # Test request to check LiteLLM connectivity by listing available models
            models = await self.client.list()
            if models:
                self.enabled = True
                bastion_logger.info(f"[{self}] Connection check successful")
            return models
        except Exception as e:
            raise Exception(f"Failed to connect to LiteLLM Proxy Router: {e}")

    def __load_client(self) -> None:
        """
        Loads the LiteLLM client using openai library.
        """
        if not settings.LITELLM_BASE_URL:
            raise ConfigurationException(
                f"[{self}] failed to load client. Model: {self.model}. LiteLLM base URL is not set."
            )

        try:
            self.client = openai.OpenAI(api_key="anything", base_url=settings.LITELLM_BASE_URL)
            self.enabled = True
        except Exception as err:
            raise Exception(
                f"[{self}][{self.model}] failed to load client. Error: {str(err)}"
            )

    async def run(self, text: str) -> PipelineResult:
        """
        Performs AI-powered analysis of the prompt using LiteLLM.

        Sends the prompt to LiteLLM router for analysis and processes the response
        to determine if the content should be blocked, allowed, or flagged
        for notification.

        Args:
            text (str): Text prompt to analyze

        Returns:
            PipelineResult: Analysis result with triggered rules or ERROR status on error
        """
        messages = self._prepare_messages(text)
        try:
            # bastion_logger.info(f"Analysis: {analysis}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            analysis = response.choices[0].message.content
            bastion_logger.info(f"Analysis: {analysis}")
            return self._process_response(analysis, text)
        except Exception as err:
            msg = f"LiteLLM - Error analyzing prompt, error={str(err)}"
            bastion_logger.error(msg)
            error_data = {
                "status": ActionStatus.ERROR,
                "reason": msg,
            }
            return self._process_response(error_data, text)