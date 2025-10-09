from app.core.enums import ActionStatus, PipelineNames
from app.managers import ALL_MANAGERS_MAP
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
        _identifier (PipelineNames): Pipeline identifier (similarity)
        enabled (bool): Whether pipeline is active (depends on OpenSearch settings)
    """

    _identifier = PipelineNames.similarity
    description = "Similarity-based pipeline for detecting similar content using vector embeddings."

    def __init__(self):
        super().__init__()
        self.similarity_manager = ALL_MANAGERS_MAP['similarity']
        if self.similarity_manager.has_active_client:
            self.enabled = True
            bastion_logger.info(f"[{self}] loaded successfully. Active client: {str(self.similarity_manager._active_client)}")
        else:
            bastion_logger.warning(f"[{self}] there are no active client. Check the Similarity Manager settings and logs.")

    async def run(self, prompt: str, **kwargs) -> PipelineResult:
        """
        Performs AI-powered analysis of the prompt using OpenAI.

        Sends the prompt to OpenAI API for analysis and processes the response
        to determine if the content should be blocked, allowed, or flagged
        for notification.

        Args:
            prompt (str): Text prompt to analyze

        Returns:
            PipelineResult: Analysis result with triggered rules or ERROR status on error
        """
        try:
            return await self.similarity_manager.run(text=prompt)
        except Exception as err:
            msg = f"Error analyzing prompt, error={str(err)}"
            bastion_logger.error(msg)
            return PipelineResult(name=str(self), triggered_rules=[], status=ActionStatus.ERROR, details=msg)
