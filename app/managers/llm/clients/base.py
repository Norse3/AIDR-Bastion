from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    pass

    @abstractmethod
    async def check_connection(self) -> None:
        pass
