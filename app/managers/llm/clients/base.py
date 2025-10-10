from abc import ABC, abstractmethod

from app.models.pipeline import PipelineResult


class BaseLLMClient(ABC):
    _identifier: str | None = None
    enabled: bool = False

    @abstractmethod
    def check_connection(self) -> None:
        pass

    @abstractmethod
    def run(self, text: str) -> PipelineResult:
        pass
