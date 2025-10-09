from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    pass

    @abstractmethod
    def check_connection(self) -> None:
        pass
