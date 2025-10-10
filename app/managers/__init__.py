from app.managers.similarity.manager import SimilarityManager
from app.managers.llm.manager import LLMManager


ALL_MANAGERS = [
    SimilarityManager(),
    LLMManager(),
]

ALL_MANAGERS_MAP = {
    manager._identifier: manager
    for manager in ALL_MANAGERS
}
