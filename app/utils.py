"""
Module for managing pipelines and their configuration.
Moved to a separate file to avoid circular imports.
"""

from typing import TYPE_CHECKING

from sentence_transformers import SentenceTransformer

from app.modules.logger import bastion_logger
from settings import get_settings

if TYPE_CHECKING:
    from app.pipelines.base import BasePipeline


settings = get_settings()

model = None
if settings.EMBEDDINGS_MODEL:
    try:
        model = SentenceTransformer(settings.EMBEDDINGS_MODEL, trust_remote_code=True, revision="main")
    except Exception as e:
        bastion_logger.error(f"Failed to load embeddings model: {e}")
        model = None


def get_pipelines_from_config(configs: list[dict]) -> dict[str, list["BasePipeline"]]:
    """
    Converts pipeline configuration from names to pipeline instances.

    Args:
        configs: List of dictionaries with pipeline configuration (names as strings)

    Returns:
        Dictionary with categories and pipeline instances
    """
    # Import here to avoid circular imports
    from app.pipelines import ENABLED_PIPELINES_MAP

    result = {}
    skipped_pipelines = set()
    for config in configs:
        pipelines = []
        flow_name = config.get("pipeline_flow")
        for pipeline_name in config.get("pipelines"):
            try:
                pipelines.append(ENABLED_PIPELINES_MAP[pipeline_name])
            except KeyError:
                skipped_pipelines.add(pipeline_name)
        if flow_name and pipelines:
            result[flow_name] = pipelines
    result["default"] = list(ENABLED_PIPELINES_MAP.values())
    if skipped_pipelines:
        bastion_logger.warning(f"Skipped pipelines: {', '.join(skipped_pipelines)}")
    return result


def text_embedding(prompt: str) -> list[float]:
    """
    Create vector embedding from text prompt.

    Args:
        prompt: Text to convert to vector

    Returns:
        List of float values representing the vector
    """
    if model is None:
        raise ValueError("Embeddings model is not loaded. Please check EMBEDDINGS_MODEL setting.")
    return model.encode(prompt, normalize_embeddings=True).tolist()
