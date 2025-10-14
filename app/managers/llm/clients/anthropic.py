import json
from typing import Any

from anthropic import AsyncAnthropic

from app.core.enums import ActionStatus, LLMClientNames
from app.core.exceptions import ConfigurationException
from app.managers.llm.clients.base import BaseLLMClient
from app.models.pipeline import PipelineResult
from app.modules.logger import bastion_logger
from settings import get_settings

settings = get_settings()


class AsyncAnthropicClient(BaseLLMClient):
    """
    Anthropic-based pipeline for analyzing prompts using Claude AI models.

    This pipeline uses Anthropic's API to analyze prompts for potential issues,
    ethical concerns, or harmful content. It leverages Claude's advanced language
    models to provide intelligent analysis and decision-making.

    Attributes:
        _client (AsyncAnthropic): Anthropic API client
        _identifier (LLMClientNames): Anthropic identifier (anthropic)
        model (str): Claude model to use for analysis
        SYSTEM_PROMPT (str): System prompt for AI analysis
    """

    _client: AsyncAnthropic
    _identifier: LLMClientNames = LLMClientNames.anthropic
    description = "Anthropic-based client for LLM operations using Claude AI models."

    def __init__(self):
        """
        Initializes Anthropic pipeline with API client and model configuration.

        Sets up the Anthropic API client with the provided API key and configures
        the model for analysis. Enables the pipeline if API key is available.
        """
        super().__init__()
        self.client = None
        model = settings.ANTHROPIC_MODEL
        self.model = model
        self.system_prompt = self._build_system_prompt()
        self.__load_client()

    def _get_additional_instructions(self) -> str:
        """
        Get Anthropic Claude-specific additional instructions.

        Returns:
            str: Additional instructions for Claude models
        """
        return """"""

    def __str__(self) -> str:
        return "Anthropic Client"

    async def check_connection(self) -> None | Any:
        """
        Checks connection to Anthropic API.

        Raises:
            Exception: On failed connection or API error
        """
        try:
            # Simple test request to check API connectivity
            # Anthropic doesn't have a list models endpoint, so we make a simple messages call
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}],
            )
            if response:
                self.enabled = True
                bastion_logger.info(f"[{self}] Connection check successful")
            return response
        except Exception as e:
            raise Exception(f"Failed to connect to Anthropic API: {e}")

    def __load_client(self) -> None:
        """
        Loads the Anthropic client.
        """
        if not settings.ANTHROPIC_API_KEY:
            raise ConfigurationException(
                f"[{self}] failed to load client. Model: {self.model}. API key is not set."
            )
        else:
            anthropic_settings = {
                "api_key": settings.ANTHROPIC_API_KEY,
            }
            # Only add base_url if it's not the default
            if (
                settings.ANTHROPIC_BASE_URL
                and settings.ANTHROPIC_BASE_URL != "https://api.anthropic.com"
            ):
                anthropic_settings["base_url"] = settings.ANTHROPIC_BASE_URL

            try:
                self.client = AsyncAnthropic(**anthropic_settings)
                self.enabled = True
            except Exception as err:
                raise Exception(
                    f"[{self}][{self.model}] failed to load client. Error: {str(err)}"
                )

    async def run(self, text: str) -> PipelineResult:
        """
        Performs AI-powered analysis of the prompt using Anthropic Claude.

        Sends the prompt to Anthropic API for analysis and processes the response
        to determine if the content should be blocked, allowed, or flagged
        for notification.

        Args:
            text (str): Text prompt to analyze

        Returns:
            PipelineResult: Analysis result with triggered rules or ERROR status on error
        """
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self.system_prompt,
                messages=[{"role": "user", "content": text}],
            )
            # Extract text from response
            analysis = response.content[0].text
            bastion_logger.info(f"Analysis: {analysis}")
            return self._process_response(analysis, text)
        except Exception as err:
            msg = f"Error analyzing prompt, error={str(err)}"
            bastion_logger.error(msg)
            error_data = {
                "status": ActionStatus.ERROR,
                "reason": msg,
            }
            return self._process_response(json.dumps(error_data), text)
