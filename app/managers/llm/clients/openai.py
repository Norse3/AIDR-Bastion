from typing import Any

from openai import AsyncOpenAI

from app.core.enums import ActionStatus, LLMClientNames
from app.core.exceptions import ConfigurationException
from app.managers.llm.clients.base import BaseLLMClient
from app.models.pipeline import PipelineResult
from app.modules.logger import bastion_logger
from settings import get_settings

settings = get_settings()


class AsyncOpenAIClient(BaseLLMClient):
    """
    OpenAI-based pipeline for analyzing prompts using AI language models.

    This pipeline uses OpenAI's API to analyze prompts for potential issues,
    ethical concerns, or harmful content. It leverages advanced language
    models to provide intelligent analysis and decision-making.

    Attributes:
        _client (AsyncOpenAI): OpenAI API client
        _identifier (LLMClientNames): OpenAI identifier (openai)
        model (str): OpenAI model to use for analysis
        SYSTEM_PROMPT (str): System prompt for AI analysis
    """

    _client: AsyncOpenAI
    _identifier: LLMClientNames = LLMClientNames.openai
    description = "OpenAI-based client for LLM operations using AI language models."

    def __init__(self):
        """
        Initializes OpenAI pipeline with API client and model configuration.

        Sets up the OpenAI API client with the provided API key and configures
        the model for analysis. Enables the pipeline if API key is available.
        """
        super().__init__()
        self.client = None
        model = settings.OPENAI_MODEL
        self.model = model
        self.system_prompt = self._build_system_prompt()
        self.__load_client()

    def _get_additional_instructions(self) -> str:
        """
        Get OpenAI-specific additional instructions.

        Returns:
            str: Additional instructions for OpenAI models
        """
        return """"""

    def __str__(self) -> str:
        return "OpenAI Client"

    async def check_connection(self) -> None | Any:
        """
        Checks connection to OpenAI API.

        Raises:
            Exception: On failed connection or API error
        """
        try:
            # Simple test request to check API connectivity
            status = await self.client.models.list()
            if status:
                self.enabled = True
                bastion_logger.info(f"[{self}] Connection check successful")
            return status
        except Exception as e:
            raise Exception(f"Failed to connect to OpenAI API: {e}")

    def __load_client(self) -> None:
        """
        Loads the OpenAI client.
        """
        if not (settings.OPENAI_API_KEY or settings.OPENAI_BASE_URL):
            raise ConfigurationException(
                f"[{self}] failed to load client. Model: {self.model}. API key or base URL is not set."
            )
        else:
            openai_settings = {
                "api_key": settings.OPENAI_API_KEY,
                "base_url": settings.OPENAI_BASE_URL,
            }
            try:
                self.client = AsyncOpenAI(**openai_settings)
                self.enabled = True
            except Exception as err:
                raise Exception(f"[{self}][{self.model}] failed to load client. Error: {str(err)}")

    async def run(self, text: str) -> PipelineResult:
        """
        Performs AI-powered analysis of the prompt using OpenAI.

        Sends the prompt to OpenAI API for analysis and processes the response
        to determine if the content should be blocked, allowed, or flagged
        for notification.

        Args:
            text (str): Text prompt to analyze

        Returns:
            PipelineResult: Analysis result with triggered rules or ERROR status on error
        """
        messages = self._prepare_messages(text)
        try:
            response = await self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=self.temperature, max_tokens=self.max_tokens
            )
            analysis = response.choices[0].message.content
            bastion_logger.info(f"Analysis: {analysis}")
            return self._process_response(analysis, text)
        except Exception as err:
            msg = f"Error analyzing prompt, error={str(err)}"
            bastion_logger.error(msg)
            error_data = {
                "status": ActionStatus.ERROR,
                "reason": msg,
            }
            return self._process_response(error_data, text)
