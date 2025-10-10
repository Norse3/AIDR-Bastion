from app.pipelines.llm_pipeline.pipeline import LLMPipeline
from app.pipelines.ml_pipeline.pipeline import MLPipeline
from app.pipelines.rule_pipeline.pipeline import RulePipeline
from app.pipelines.ca_pipeline.pipeline import CodeAnalysisPipeline
from app.pipelines.similarity_pipeline.pipeline import SimilarityPipeline

__PIPELINES__ = [
    SimilarityPipeline(),
    CodeAnalysisPipeline(),
    RulePipeline(),
    MLPipeline(),
    LLMPipeline(),
]


ENABLED_PIPELINES_MAP = {
    pipeline._identifier: pipeline
    for pipeline in __PIPELINES__ 
    if pipeline.enabled
}

PIPELINES_MAP = {
    pipeline._identifier: pipeline
    for pipeline in __PIPELINES__
}
