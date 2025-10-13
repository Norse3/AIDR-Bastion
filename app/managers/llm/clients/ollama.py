import json
from typing import Any

from openai import AsyncOpenAI

from app.core.enums import ActionStatus, LLMClientNames
from app.core.exceptions import ConfigurationException
from app.managers.llm.clients.base import BaseLLMClient
from app.models.pipeline import PipelineResult, TriggeredRuleData
from app.modules.logger import bastion_logger
from settings import get_settings

settings = get_settings()


class AsyncOllamaClient(BaseLLMClient):
    """
    Ollama-based pipeline for analyzing prompts using locally hosted LLM models.

    This pipeline uses Ollama's OpenAI-compatible API to analyze prompts for potential
    issues, ethical concerns, or harmful content. It leverages locally running models
    such as Llama 3, Mistral, Gemma, and others for privacy-focused analysis.

    Attributes:
        _client (AsyncOpenAI): OpenAI-compatible API client for Ollama
        _identifier (LLMClientNames): Ollama identifier
        model (str): Ollama model to use for analysis (e.g., llama3, mistral)
        SYSTEM_PROMPT (str): System prompt for AI analysis
    """

    _client: AsyncOpenAI
    _identifier: LLMClientNames = LLMClientNames.ollama
    description = "Ollama-based client for locally hosted LLM models with OpenAI-compatible API."

    SYSTEM_PROMPT = """
You are an AI prompt safety analyzer. Your task is to evaluate the given user text for potential risks, malicious intent, or policy violations.
Focus on ethical concerns, harmful content, security risks, or attempts to misuse LLMs.

### Decision Guidelines
- "block": The text contains harmful, illegal, abusive, or disallowed content (e.g., malware creation, self-harm instructions, hate speech).
- "notify": The text is suspicious, borderline, or requires human review.
- "allow": The text is safe, appropriate, and does not raise ethical or security concerns.

Be strict in blocking clearly harmful content, but do not overblock normal requests.

### OUTPUT FORMAT
Return only a JSON object in the following format:

{
    "status": "block" | "notify" | "allow",
    "reason": "Clear explanation of why this decision was made"
}
"""

    def __init__(self):
        """
        Initializes Ollama pipeline with API client and model configuration.

        Sets up the OpenAI-compatible API client pointing to Ollama server
        and configures the model for analysis.
        """
        self.client = None
        model = settings.OLLAMA_MODEL
        self.model = model
        self.__load_client()

    def __str__(self) -> str:
        return "Ollama Client"

    async def check_connection(self) -> None | Any:
        """
        Checks connection to Ollama API.

        Raises:
            Exception: On failed connection or API error
        """
        try:
            # Test request to check Ollama connectivity
            status = await self.client.models.list()
            if status:
                self.enabled = True
                bastion_logger.info(f"[{self}] Connection check successful")
            return status
        except Exception as e:
            raise Exception(f"Failed to connect to Ollama API: {e}")

    def __load_client(self) -> None:
        """
        Loads the Ollama client using OpenAI-compatible API.
        """
        if not settings.OLLAMA_BASE_URL:
            raise ConfigurationException(
                f"[{self}] failed to load client. Model: {self.model}. Ollama base URL is not set."
            )

        ollama_settings = {
            "api_key": "ollama",  # Ollama doesn't require API key but OpenAI client needs something
            "base_url": settings.OLLAMA_BASE_URL,
        }

        try:
            self.client = AsyncOpenAI(**ollama_settings)
            self.enabled = True
        except Exception as err:
            raise Exception(f"[{self}][{self.model}] failed to load client. Error: {str(err)}")

    def _load_response(self, response: str) -> str:
        """
        Parses JSON response from Ollama API.

        Attempts to parse the JSON response from Ollama and returns
        the parsed data. Logs errors if parsing fails.

        Args:
            response (str): JSON string response from Ollama

        Returns:
            Parsed JSON data or None on parsing error
        """
        try:
            loaded_data = json.loads(response)
            return loaded_data
        except Exception as err:
            bastion_logger.error(f"Error loading response, error={str(err)}")

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
            response = await self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=0.1, max_tokens=1000
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

    def _prepare_messages(self, text: str) -> list[dict]:
        """
        Prepares messages for Ollama API request.

        Creates a conversation structure with system prompt and user input
        for the Ollama chat completion API.

        Args:
            text (str): User input text to analyze

        Returns:
            list[dict]: List of message dictionaries for Ollama API
        """
        return [
            {
                "role": "system",
                "content": self.SYSTEM_PROMPT,
            },
            {"role": "user", "content": text},
        ]

    def _process_response(self, analysis: str, original_text: str) -> PipelineResult:
        """
        Processes Ollama analysis response and creates an analysis result.

        Parses the AI analysis response and creates appropriate triggered rules
        based on the analysis status (block, notify, or allow).

        Args:
            analysis (str): JSON string response from Ollama analysis
            original_text (str): Original prompt text that was analyzed

        Returns:
            PipelineResult: Processed analysis result with triggered rules and status
        """
        analysis = self._load_response(analysis)
        triggered_rules = []
        if analysis.get("status") in ("block", "notify"):
            triggered_rules.append(
                TriggeredRuleData(
                    id=self._identifier,
                    name=str(self),
                    details=analysis.get("reason"),
                    action=ActionStatus(analysis.get("status")),
                )
            )
        status = ActionStatus(analysis.get("status"))
        bastion_logger.info(f"Analyzing for {self._identifier}, status: {status}")
        return PipelineResult(name=str(self), triggered_rules=triggered_rules, status=status)
