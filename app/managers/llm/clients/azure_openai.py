import json
from typing import Any

from openai import AsyncAzureOpenAI

from app.core.enums import ActionStatus, LLMClientNames
from app.core.exceptions import ConfigurationException
from app.managers.llm.clients.base import BaseLLMClient
from app.models.pipeline import PipelineResult
from app.modules.logger import bastion_logger
from settings import get_settings

settings = get_settings()


class AsyncAzureOpenAIClient(BaseLLMClient):
    """
    Azure OpenAI-based pipeline for analyzing prompts using GPT models via Azure.

    This pipeline uses Azure OpenAI Service to analyze prompts for potential issues,
    ethical concerns, or harmful content. It leverages Microsoft's Azure infrastructure
    to provide enterprise-grade AI analysis with enhanced security and compliance.

    Attributes:
        _client (AsyncAzureOpenAI): Azure OpenAI API client
        _identifier (LLMClientNames): Azure OpenAI identifier
        model (str): Azure OpenAI model deployment name
        SYSTEM_PROMPT (str): System prompt for AI analysis
    """

    _client: AsyncAzureOpenAI
    _identifier: LLMClientNames = LLMClientNames.azure
    description = (
        "Azure OpenAI-based client for GPT models via Microsoft Azure infrastructure."
    )

    def __init__(self):
        """
        Initializes Azure OpenAI pipeline with API client and model configuration.

        Sets up the Azure OpenAI API client with the provided endpoint, API key, and
        configures the model deployment for analysis.
        """
        super().__init__()
        self.client = None
        model = settings.AZURE_OPENAI_DEPLOYMENT
        self.model = model
        self.system_prompt = self._build_system_prompt()
        self.__load_client()

    def _get_additional_instructions(self) -> str:
        """
        Get Azure OpenAI-specific additional instructions.

        Returns:
            str: Additional instructions for Azure OpenAI models
        """
        return """"""

    def __str__(self) -> str:
        return "Azure OpenAI Client"

    async def check_connection(self) -> None | Any:
        """
        Checks connection to Azure OpenAI API.

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
            raise Exception(f"Failed to connect to Azure OpenAI API: {e}")

    def __load_client(self) -> None:
        """
        Loads the Azure OpenAI client.
        """
        if not (settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY):
            raise ConfigurationException(
                f"[{self}] failed to load client. Model: {self.model}. Azure endpoint or API key is not set."
            )

        azure_settings = {
            "api_key": settings.AZURE_OPENAI_API_KEY,
            "azure_endpoint": settings.AZURE_OPENAI_ENDPOINT,
            "api_version": settings.AZURE_OPENAI_API_VERSION,
        }

        try:
            self.client = AsyncAzureOpenAI(**azure_settings)
            self.enabled = True
        except Exception as err:
            raise Exception(
                f"[{self}][{self.model}] failed to load client. Error: {str(err)}"
            )

    async def run(self, text: str) -> PipelineResult:
        """
        Performs AI-powered analysis of the prompt using Azure OpenAI.

        Sends the prompt to Azure OpenAI API for analysis and processes the response
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
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
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
            return self._process_response(json.dumps(error_data), text)
