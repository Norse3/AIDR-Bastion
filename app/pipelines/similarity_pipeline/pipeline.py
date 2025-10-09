from app.core.enums import ActionStatus, PipelineNames
from app.managers.similarity.manager import similarity_manager
from app.models.pipeline import PipelineResult
from app.modules.logger import bastion_logger
from app.pipelines.base import BasePipeline
from settings import get_settings

settings = get_settings()


class SimilarityPipeline(BasePipeline):
    """
    Similarity-based pipeline for detecting similar content using vector embeddings.

    This pipeline uses vector embeddings and OpenSearch to find similar documents
    in a knowledge base. It splits prompts into sentences, converts them to
    embeddings, and searches for similar content using cosine similarity.
    Results are deduplicated and scored based on similarity thresholds.

    Attributes:
        name (PipelineNames): Pipeline name (similarity)
        enabled (bool): Whether pipeline is active (depends on OpenSearch settings)
    """

    name = PipelineNames.similarity

    def __init__(self):
        super().__init__()
        if similarity_manager.has_active_client:
            self.enabled = True
            bastion_logger.info(f"[{self}] loaded successfully. Active client: {similarity_manager.active_client}")
        else:
            bastion_logger.warning(f"[{self}] failed to load Active client: {similarity_manager.active_client}")

    async def run(self, prompt: str) -> PipelineResult:
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
            return await similarity_manager.run(prompt=prompt)
        except Exception as err:
            bastion_logger.error(f"Error analyzing prompt, error={str(err)}")
            return PipelineResult(name=str(self), triggered_rules=[], status=ActionStatus.ERROR, details=str(err))