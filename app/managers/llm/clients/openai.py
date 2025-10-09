import json

from openai import AsyncOpenAI

from app.core.enums import ActionStatus
from app.core.exceptions import ConfigurationException
from app.managers.llm.clients.base import BaseLLMClient
from app.models.pipeline import PipelineResult, TriggeredRuleData
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
        _identifier (str): OpenAI identifier (openai)
        model (str): OpenAI model to use for analysis
        SYSTEM_PROMPT (str): System prompt for AI analysis
    """

    _client: AsyncOpenAI
    _identifier = "openai"

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
        Initializes OpenAI pipeline with API client and model configuration.

        Sets up the OpenAI API client with the provided API key and configures
        the model for analysis. Enables the pipeline if API key is available.
        """
        self.client = None
        model = settings.OPENAI_MODEL
        self.model = model
        self.__load_client()

    def __str__(self) -> str:
        return "OpenAI Client"

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

    def _load_response(self, response: str) -> str:
        """
        Parses JSON response from OpenAI API.

        Attempts to parse the JSON response from OpenAI and returns
        the parsed data. Logs errors if parsing fails.

        Args:
            response (str): JSON string response from OpenAI

        Returns:
            Parsed JSON data or None on parsing error
        """
        try:
            loadded_data = json.loads(response)
            return loadded_data
        except Exception as err:
            bastion_logger.error(f"Error loading response, error={str(err)}")

    async def validate_input_text(self, prompt: str) -> PipelineResult | None:
        """
        Performs AI-powered analysis of the prompt using OpenAI.

        Sends the prompt to OpenAI API for analysis and processes the response
        to determine if the content should be blocked, allowed, or flagged
        for notification.

        Args:
            prompt (str): Text prompt to analyze

        Returns:
            PipelineResult: Analysis result with triggered rules or None on error
        """
        messages = self._prepare_messages(prompt)
        try:
            response = await self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=0.1, max_tokens=1000
            )
            analysis = response.choices[0].message.content
            bastion_logger.info(f"Analysis: {analysis}")
            return self._process_response(analysis, prompt)
        except Exception as err:
            bastion_logger.error(f"Error analyzing prompt, error={str(err)}")
            error_data = {
                "status": ActionStatus.ERROR,
                "reason": str(err),
            }
            return self._process_response(error_data, prompt)

    def _prepare_messages(self, text: str) -> list[dict]:
        """
        Prepares messages for OpenAI API request.

        Creates a conversation structure with system prompt and user input
        for the OpenAI chat completion API.

        Args:
            text (str): User input text to analyze

        Returns:
            list[dict]: List of message dictionaries for OpenAI API
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
        Processes OpenAI analysis response and creates an analysis result.

        Parses the AI analysis response and creates appropriate triggered rules
        based on the analysis status (block, notify, or allow).

        Args:
            analysis (str): JSON string response from OpenAI analysis
            original_text (str): Original prompt text that was analyzed

        Returns:
            PipelineResult: Processed analysis result with triggered rules and status
        """
        analysis = self._load_response(analysis)
        triggered_rules = []
        if analysis.get("status") in ("block", "notify"):
            triggered_rules.append(
                TriggeredRuleData(
                    id=self.name,
                    name=self.name,
                    details=analysis.get("reason"),
                    action=ActionStatus(analysis.get("status")),
                )
            )
        status = ActionStatus(analysis.get("status"))
        bastion_logger.info(f"Analyzing for {self.name}, status: {status}")
        return PipelineResult(name=str(self), triggered_rules=triggered_rules, status=status)
