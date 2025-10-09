from fastapi import APIRouter, HTTPException

from app.managers import ALL_MANAGERS_MAP
from app.models.manager import (
    ManagersListResponse,
    ManagerInfo,
    SwitchActiveClientRequest,
    SwitchActiveClientResponse,
)


manager_router = APIRouter(prefix="/manager", tags=["Client Manager API"])


@manager_router.get("/list")
async def get_managers() -> ManagersListResponse:
    """
    Get list of all available managers and their clients.

    Returns:
        ManagersListResponse: List of managers with client information
    """
    managers = []

    for manager_id, manager in ALL_MANAGERS_MAP.items():
        managers.append(
            ManagerInfo(
                id=manager_id,
                name=str(manager),
                enabled=manager.has_active_client,
                clients=manager.get_available_clients()
            )
        )

    return ManagersListResponse(managers=managers)


@manager_router.get("/{manager_id}")
async def get_manager(manager_id: str) -> ManagerInfo:
    """
    Get information about a specific manager.
    """
    try:
        manager = ALL_MANAGERS_MAP[manager_id]
        return ManagerInfo(
            id=manager_id,
            name=str(manager),
            enabled=manager.has_active_client,
            clients=manager.get_available_clients()
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Manager not found")


@manager_router.post("/switch_active_client")
async def switch_active_client(request: SwitchActiveClientRequest) -> SwitchActiveClientResponse:
    """
    Get list of all available managers and their clients.

    Returns:
        ManagersListResponse: List of managers with client information
    """
    status = False

    if manager := ALL_MANAGERS_MAP.get(request.manager_id):
        status = manager.switch_active_client(request.client_id)

    return SwitchActiveClientResponse(client_id=request.client_id, status=status)
