from app.core.enums import ActionStatus, PipelineNames
from app.managers.llm.manager import llm_manager
from app.models.pipeline import PipelineResult
from app.modules.logger import bastion_logger
from app.pipelines.base import BasePipeline
from settings import get_settings

settings = get_settings()


class LLMPipeline(BasePipeline):
    """
    OpenAI-based pipeline for analyzing prompts using AI language models.

    This pipeline uses OpenAI's API to analyze prompts for potential issues,
    ethical concerns, or harmful content. It leverages advanced language
    models to provide intelligent analysis and decision-making.

    Attributes:
        name (PipelineNames): Pipeline name (llm)
        client (AsyncOpenAI): OpenAI API client
        model (str): OpenAI model to use for analysis
        enabled (bool): Whether pipeline is active (depends on API key availability)
        SYSTEM_PROMPT (str): System prompt for AI analysis
    """

    name = PipelineNames.llm

    def __init__(self):
        """
        Initializes OpenAI pipeline with API client and model configuration.

        Sets up the OpenAI API client with the provided API key and configures
        the model for analysis. Enables the pipeline if API key is available.
        """
        if llm_manager.has_active_client:
            self.enabled = True
            bastion_logger.info(f"[{self}] loaded successfully. Active client: {llm_manager.active_client}")
        else:
            bastion_logger.warning(f"[{self}] failed to load Active client: {llm_manager.active_client}")

    def __str__(self) -> str:
        return "LLM Pipeline"

    async def run(self, prompt: str) -> PipelineResult | None:
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
        try:
            return await llm_manager.validate_input_text(prompt=prompt)
        except Exception as err:
            bastion_logger.error(f"Error analyzing prompt, error={str(err)}")
            return PipelineResult(name=str(self), triggered_rules=[], status=ActionStatus.ERROR, details=str(err))
