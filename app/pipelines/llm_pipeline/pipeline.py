from app.core.enums import ActionStatus, PipelineNames
from app.managers import ALL_MANAGERS_MAP
from app.models.pipeline import PipelineResult
from app.modules.logger import bastion_logger
from app.pipelines.base import BasePipeline
from settings import get_settings

settings = get_settings()


class LLMPipeline(BasePipeline):
    """
    LLM-based pipeline for analyzing prompts using AI language models.

    This pipeline uses LLM's API to analyze prompts for potential issues,
    ethical concerns, or harmful content. It leverages advanced language
    models to provide intelligent analysis and decision-making.

    Attributes:
        _identifier (PipelineNames): Pipeline identifier (llm)
        client (BaseLLMClient): LLM API client
        model (str): LLM model to use for analysis
        enabled (bool): Whether pipeline is active (depends on API key availability)
        SYSTEM_PROMPT (str): System prompt for AI analysis
    """

    _identifier = PipelineNames.llm
    description = "LLM-based pipeline for analyzing prompts using AI language models."

    def __init__(self):
        """
        Initializes LLM pipeline with API client and model configuration.

        Sets up the LLM API client with the provided API key and configures
        the model for analysis. Enables the pipeline if API key is available.
        """
        self.llm_manager = ALL_MANAGERS_MAP['llm']
        if self.llm_manager.has_active_client:
            self.enabled = True
            bastion_logger.info(f"[{self}] loaded successfully. Active client: {str(self.llm_manager._active_client)}")
        else:
            bastion_logger.warning(f"[{self}] there are no active client. Check the LLM Manager settings and logs.")

    def __str__(self) -> str:
        return "LLM Pipeline"

    async def run(self, prompt: str) -> PipelineResult:
        """
        Performs AI-powered analysis of the prompt using LLM.

        Sends the prompt to LLM API for analysis and processes the response
        to determine if the content should be blocked, allowed, or flagged
        for notification.

        Args:
            prompt (str): Text prompt to analyze

        Returns:
            PipelineResult: Analysis result with triggered rules or None on error
        """
        try:
            return await self.llm_manager.validate_input_text(prompt=prompt)
        except Exception as err:
            bastion_logger.error(f"Error analyzing prompt, error={str(err)}")
            return PipelineResult(name=str(self), triggered_rules=[], status=ActionStatus.ERROR, details=str(err))
