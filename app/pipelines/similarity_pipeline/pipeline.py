import asyncio

from app.core.enums import PipelineNames, RuleAction
from app.managers.similarity.manager import similarity_manager
from app.models.pipeline import PipelineResult, TriggeredRuleData
from app.modules.logger import bastion_logger
from app.pipelines.base import BasePipeline
from app.pipelines.similarity_pipeline.utils import split_text_into_sentences
from app.utils import text_embedding
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

    def __split_prompt_into_sentences(self, prompt: str) -> list[str]:
        """
        Split prompt into sentences and return them as a list.

        Args:
            prompt (str): Text prompt to split

        Returns:
            list[str]: List of sentences from the prompt
        """
        return split_text_into_sentences(prompt)

    async def __search_similar_documents(self, chunk: str) -> list[dict]:
        """
        Search for similar documents using vector embeddings.

        Converts text chunk to vector embedding and searches OpenSearch
        for similar documents. Filters results by similarity threshold
        and formats them for further processing.

        Args:
            chunk (str): Text chunk to search for similar content

        Returns:
            list[dict]: List of similar documents with metadata and scores
        """
        vector = text_embedding(chunk)
        similar_documents = await similarity_manager.search_similar_documents(vector)
        return [
            {
                "action": self._get_action(doc["_score"]),
                "doc_id": doc["_source"].get("id"),
                "name": doc["_source"].get("category"),
                "details": doc["_source"]["details"],
                "body": doc["_source"]["text"],
                "score": doc["_score"],
            }
            for doc in similar_documents
            if doc["_score"] > settings.SIMILARITY_NOTIFY_THRESHOLD
        ]

    async def __prepare_triggered_rules(self, similar_documents: list[dict]) -> list[TriggeredRuleData]:
        """
        Prepare rules with deduplication by doc_id.

        For identical documents, preference is given to those with higher score.
        Converts similar documents to TriggeredRuleData objects.

        Args:
            similar_documents (list[dict]): List of documents with search results

        Returns:
            list[TriggeredRuleData]: List of unique TriggeredRuleData objects
        """
        deduplicated_docs = {}
        for doc in similar_documents:
            doc_id = doc["doc_id"]
            if doc_id not in deduplicated_docs or doc["score"] > deduplicated_docs[doc_id]["score"]:
                deduplicated_docs[doc_id] = doc
        return [
            TriggeredRuleData(
                action=doc["action"], id=doc["doc_id"], name=doc["name"], details=doc["details"], body=doc["body"]
            )
            for doc in deduplicated_docs.values()
        ]

    async def run(self, prompt: str, **kwargs) -> PipelineResult:
        """
        Analyzes prompt for similar content using vector similarity search.

        Splits the prompt into sentences, processes them in batches,
        and searches for similar documents using vector embeddings.
        Returns analysis results with triggered rules for similar content.

        Args:
            prompt (str): Text prompt to analyze for similar content
            **kwargs: Additional keyword arguments (unused)

        Returns:
            PipelineResult: Analysis result with triggered rules and status
        """
        similar_documents = []
        chunks = self.__split_prompt_into_sentences(prompt)
        bastion_logger.info(f"Analyzing for {len(chunks)} sentences")

        batch_size = 5
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            tasks = [self.__search_similar_documents(chunk) for chunk in batch]
            batch_results = await asyncio.gather(*tasks)
            for result in batch_results:
                similar_documents.extend(result)
        triggered_rules = await self.__prepare_triggered_rules(similar_documents)
        bastion_logger.info(f"Found {len(triggered_rules)} similar documents")
        return PipelineResult(
            name=str(self), status=self._pipeline_status(triggered_rules), triggered_rules=triggered_rules
        )

    @staticmethod
    def _get_action(score: float) -> RuleAction:
        """
        Determines action based on similarity score.

        Compares the similarity score against configured thresholds
        to determine whether to block or notify.

        Args:
            score (float): Similarity score from vector search

        Returns:
            RuleAction: BLOCK if score exceeds block threshold, otherwise NOTIFY
        """
        if score >= settings.SIMILARITY_BLOCK_THRESHOLD:
            return RuleAction.BLOCK
        return RuleAction.NOTIFY
