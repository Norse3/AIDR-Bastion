from pydantic import BaseModel


class ClientInfo(BaseModel):
    id: str
    name: str
    description: str


class ManagerInfo(BaseModel):
    id: str
    name: str
    enabled: bool
    clients: list[ClientInfo]


class ManagersListResponse(BaseModel):
    managers: list[ManagerInfo]


class SwitchActiveClientRequest(BaseModel):
    manager_id: str
    client_id: str


class SwitchActiveClientResponse(BaseModel):
    status: bool
    client_id: str
