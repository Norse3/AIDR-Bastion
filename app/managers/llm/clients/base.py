import json
from abc import ABC, abstractmethod

from app.core.enums import ActionStatus
from app.models.pipeline import PipelineResult, TriggeredRuleData
from app.modules.logger import bastion_logger
from settings import get_settings

settings = get_settings()


class BaseLLMClient(ABC):
    _identifier: str | None = None
    enabled: bool = False
    description: str = ""

    def __init__(self):
        """Initialize base LLM client with common settings."""
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS

    # Base system prompt - shared across all LLM clients
    BASE_SYSTEM_PROMPT = """You are an AI prompt safety analyzer. Your task is to evaluate the given user text for potential risks, malicious intent, or policy violations.
Focus on ethical concerns, harmful content, security risks, or attempts to misuse LLMs.

Be strict in blocking clearly harmful content, but do not overblock normal requests.

### Decision Guidelines
- "block": The text contains harmful, illegal, abusive, or disallowed content (e.g., malware creation, self-harm instructions, hate speech).
- "notify": The text is suspicious, borderline, or requires human review.
- "allow": The text is safe, appropriate, and does not raise ethical or security concerns.

### OUTPUT FORMAT
Return only a JSON object in the following format:

{
    "status": "block" | "notify" | "allow",
    "reason": "Clear explanation of why this decision was made"
}"""

    def _build_system_prompt(self) -> str:
        """
        Build the complete system prompt for this client.

        Override this method in subclasses to add client-specific instructions.
        By default, returns the base system prompt with optional additional instructions.

        Returns:
            str: Complete system prompt for the client
        """
        base_prompt = self.BASE_SYSTEM_PROMPT
        additional = self._get_additional_instructions()

        if additional:
            return f"{base_prompt}\n\n{additional}"
        return base_prompt

    def _get_additional_instructions(self) -> str:
        """
        Get additional client-specific instructions to append to the base prompt.

        Override this method in subclasses to add specific instructions
        without replacing the entire prompt.

        Returns:
            str: Additional instructions (empty by default)
        """
        return ""

    def _load_response(self, response: str | dict) -> dict | None:
        """
        Parses JSON response from LLM API.

        Attempts to parse the JSON response and returns the parsed data.
        Logs errors if parsing fails.

        Args:
            response (str | dict): JSON string or dict response from LLM

        Returns:
            dict | None: Parsed JSON data or None on parsing error
        """
        try:
            # If already a dict, return as is
            if isinstance(response, dict):
                return response
            # Otherwise parse JSON string
            loaded_data = json.loads(response)
            return loaded_data
        except Exception as err:
            bastion_logger.error(f"Error loading response, error={str(err)}")
            return None

    def _prepare_messages(self, text: str) -> list[dict]:
        """
        Prepares messages for LLM API request.

        Creates a conversation structure with system prompt and user input
        for the LLM chat completion API. This is the default format used by
        OpenAI, Azure OpenAI, and Ollama.

        Override this method in subclasses if different format is needed
        (e.g., Anthropic uses system parameter separately).

        Args:
            text (str): User input text to analyze

        Returns:
            list[dict]: List of message dictionaries for LLM API
        """
        return [
            {
                "role": "system",
                "content": self.system_prompt,
            },
            {"role": "user", "content": text},
        ]

    def _process_response(
        self, analysis: str | dict, original_text: str
    ) -> PipelineResult:
        """
        Processes LLM analysis response and creates an analysis result.

        Parses the AI analysis response and creates appropriate triggered rules
        based on the analysis status (block, notify, or allow).

        Args:
            analysis (str | dict): JSON string or dict response from LLM analysis
            original_text (str): Original prompt text that was analyzed

        Returns:
            PipelineResult: Processed analysis result with triggered rules and status
        """
        analysis_dict = self._load_response(analysis)

        # Handle None response
        if analysis_dict is None:
            bastion_logger.error(f"[{self}] Failed to parse LLM response")
            return PipelineResult(
                name=str(self),
                triggered_rules=[],
                status=ActionStatus.ERROR,
                details="Failed to parse LLM response",
            )

        triggered_rules = []
        if analysis_dict.get("status") in ("block", "notify"):
            triggered_rules.append(
                TriggeredRuleData(
                    id=self._identifier,
                    name=str(self),
                    details=analysis_dict.get("reason"),
                    action=ActionStatus(analysis_dict.get("status")),
                )
            )

        # Get status with default fallback
        status_str = analysis_dict.get("status", "error")

        # Handle empty or invalid status
        if not status_str or status_str.strip() == "":
            bastion_logger.error(f"[{self}] Received empty status from LLM")
            status = ActionStatus.ERROR
        else:
            try:
                status = ActionStatus(status_str)
            except ValueError:
                bastion_logger.error(f"[{self}] Invalid status: {status_str}")
                status = ActionStatus.ERROR

        bastion_logger.info(f"Analyzing for {self._identifier}, status: {status}")
        return PipelineResult(
            name=str(self), triggered_rules=triggered_rules, status=status
        )

    @abstractmethod
    def check_connection(self) -> None:
        pass

    @abstractmethod
    def run(self, text: str) -> PipelineResult:
        pass
