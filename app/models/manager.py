from pydantic import BaseModel
from app.core.enums import ManagerNames, LLMClientNames, SimilarityClientNames


class ClientInfo(BaseModel):
    id: LLMClientNames | SimilarityClientNames
    name: str
    description: str


class ManagerInfo(BaseModel):
    id: ManagerNames
    name: str
    enabled: bool
    description: str
    clients: list[ClientInfo]


class ManagersListResponse(BaseModel):
    managers: list[ManagerInfo]


class SwitchActiveClientRequest(BaseModel):
    manager_id: ManagerNames
    client_id: LLMClientNames | SimilarityClientNames


class SwitchActiveClientResponse(BaseModel):
    status: bool
    client_id: LLMClientNames | SimilarityClientNames
