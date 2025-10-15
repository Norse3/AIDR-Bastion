from typing import Any

import ollama

from app.core.enums import ActionStatus, LLMClientNames
from app.core.exceptions import ConfigurationException
from app.managers.llm.clients.base import BaseLLMClient
from app.models.pipeline import PipelineResult
from app.modules.logger import bastion_logger
from settings import get_settings

settings = get_settings()


class AsyncOllamaClient(BaseLLMClient):
    """
    Ollama-based pipeline for analyzing prompts using locally hosted LLM models.

    This pipeline uses Ollama's official Python library to analyze prompts for potential
    issues, ethical concerns, or harmful content. It leverages locally running models
    such as Llama 3, Mistral, Gemma, and others for privacy-focused analysis.

    Attributes:
        _client (ollama.AsyncClient): Official Ollama async client
        _identifier (LLMClientNames): Ollama identifier
        model (str): Ollama model to use for analysis (e.g., llama3, mistral)
        SYSTEM_PROMPT (str): System prompt for AI analysis
    """

    _client: ollama.AsyncClient
    _identifier: LLMClientNames = LLMClientNames.ollama
    description = "Ollama-based client for locally hosted LLM models using official Ollama library."

    def __init__(self):
        """
        Initializes Ollama pipeline with API client and model configuration.

        Sets up the official Ollama async client pointing to Ollama server
        and configures the model for analysis.
        """
        super().__init__()
        self.client = None
        model = settings.OLLAMA_MODEL
        self.model = model
        self.system_prompt = self._build_system_prompt()
        self.__load_client()

    def _get_additional_instructions(self) -> str:
        """
        Get Ollama-specific additional instructions.

        Returns:
            str: Additional instructions for Ollama models
        """
        return """### Ollama-Specific Instructions
- Provide concise and structured responses
- Always return valid JSON format as specified above
- Focus on accurate threat detection for local LLM deployments"""

    def __str__(self) -> str:
        return "Ollama Client"

    async def check_connection(self) -> None | Any:
        """
        Checks connection to Ollama API.

        Raises:
            Exception: On failed connection or API error
        """
        try:
            # Test request to check Ollama connectivity by listing available models
            models = await self.client.list()
            if models:
                self.enabled = True
                bastion_logger.info(f"[{self}] Connection check successful")
            return models
        except Exception as e:
            raise Exception(f"Failed to connect to Ollama API: {e}")

    def __load_client(self) -> None:
        """
        Loads the Ollama client using official Ollama library.
        """
        if not settings.OLLAMA_BASE_URL:
            raise ConfigurationException(
                f"[{self}] failed to load client. Model: {self.model}. Ollama base URL is not set."
            )

        # Extract host from OLLAMA_BASE_URL
        # Remove /v1 suffix if present since official library doesn't use it
        host = settings.OLLAMA_BASE_URL.rstrip("/")
        if host.endswith("/v1"):
            host = host[:-3]

        try:
            self.client = ollama.AsyncClient(host=host)
            self.enabled = True
        except Exception as err:
            raise Exception(
                f"[{self}][{self.model}] failed to load client. Error: {str(err)}"
            )

    async def run(self, text: str) -> PipelineResult:
        """
        Performs AI-powered analysis of the prompt using Ollama.

        Sends the prompt to Ollama API for analysis and processes the response
        to determine if the content should be blocked, allowed, or flagged
        for notification.

        Args:
            text (str): Text prompt to analyze

        Returns:
            PipelineResult: Analysis result with triggered rules or ERROR status on error
        """
        messages = self._prepare_messages(text)
        try:
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                format="json",  # Force JSON response format
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            )

            # Debug logging
            bastion_logger.debug(f"Ollama response type: {type(response)}")
            bastion_logger.debug(f"Ollama response: {response}")

            # Handle dict response
            if isinstance(response, dict):
                analysis = response.get("message", {}).get("content")
            else:
                # Handle response object with attributes
                analysis = (
                    response.get("message", {}).get("content")
                    if hasattr(response, "get")
                    else (
                        getattr(response.message, "content", None)
                        if hasattr(response, "message")
                        else None
                    )
                )

            if analysis is None:
                bastion_logger.error(
                    f"Failed to extract content from response: {response}"
                )
                return PipelineResult(
                    name=str(self),
                    triggered_rules=[],
                    status=ActionStatus.ERROR,
                    details="Failed to extract content from Ollama response",
                )

            bastion_logger.info(f"Analysis: {analysis}")
            return self._process_response(analysis, text)
        except Exception as err:
            msg = f"Error analyzing prompt, error={str(err)}"
            bastion_logger.error(msg)
            return PipelineResult(
                name=str(self),
                triggered_rules=[],
                status=ActionStatus.ERROR,
                details=msg,
            )
