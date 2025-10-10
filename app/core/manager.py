from abc import ABC, abstractmethod
from typing import Dict, Generic, List, TypeVar

from app.core.exceptions import ConfigurationException
from app.modules.logger import bastion_logger
from settings import get_settings

settings = get_settings()

T = TypeVar("T")  # Type for client instances


class BaseManager(ABC, Generic[T]):
    """
    Base manager class for managing different types of clients.

    This class provides common functionality for managing multiple client instances,
    including initialization, client switching, and active client management.
    It uses generics to support different types of clients while maintaining
    type safety.

    Attributes:
        _clients_map (Dict[str, T]): Mapping of client identifiers to client instances
        _active_client (Optional[T]): Currently active client for operations
        _active_client_id (Optional[str]): Identifier of the active client
    """

    def __init__(self, clients_map: Dict[str, type], default_client_setting: str) -> None:
        """
        Initializes BaseManager with available clients.

        Args:
            clients_map (Dict[str, type]): Mapping of client identifiers to client classes
            default_client_setting (str): Setting name for default client
        """
        self._clients_map: Dict[str, T] = {}
        self._active_client: None | T = None
        self._active_client_id: None | str = None
        self._default_client_setting = default_client_setting

        self._initialize_clients(clients_map)

    def __str__(self) -> str:
        """
        String representation of the client.

        Returns:
            str: Class name of the client
        """
        return self.__class__.__name__

    def __repr__(self) -> str:
        """
        String representation of the client.

        Returns:
            str: Class name of the client
        """
        return self.__str__()

    def _initialize_clients(self, clients_map: Dict[str, type]) -> None:
        """
        Initializes available clients based on provided clients map.

        Args:
            clients_map (Dict[str, type]): Mapping of client identifiers to client classes
        """
        for client_id, client_class in clients_map.items():
            try:
                client = client_class()
                self._clients_map[client_id] = client
                bastion_logger.info(f"[{client}] initialized successfully")
            except ConfigurationException as e:
                bastion_logger.error(f"[{client_class._identifier}] There are no configuration. Error: {e}")
            except Exception as e:
                bastion_logger.error(f"[{client_class._identifier}] Failed to initialize. Error: {e}")

    async def _activate_clients(self) -> None:
        """
        Activates all initialized clients.
        """
        await self._check_connections()
        self._set_active_client()

    @abstractmethod
    async def _check_connections(self) -> None:
        """
        Checks connections for all initialized clients.
        """
        pass

    def _set_active_client(self, client_id: str = None) -> None:
        """
        Sets the active client based on provided client_id or default setting.

        Args:
            client_id (str, optional): Client identifier to set as active
        """
        if client_id is None:
            client_id = getattr(settings, self._default_client_setting, None)

        if client := self._clients_map.get(client_id):
            if client.enabled is False:
                bastion_logger.warning(f"[{self}][{client}] Client is not enabled. Check configuration.")
                return
            self._active_client = client
            self._active_client_id = client_id
            bastion_logger.info(f"[{self}][{client}] Set as active client")
        elif not self._active_client and self._clients_map:
            self._active_client = next(iter(self._clients_map.values()))
            self._active_client_id = getattr(self._active_client, "identifier", None)
            bastion_logger.info(f"Switched active client to {self._active_client_id}")
        else:
            bastion_logger.warning(f"Cannot switch to client '{client_id}': client not available")

    @property
    def has_active_client(self) -> bool:
        """
        Returns True if an active client is available, False otherwise.

        Returns:
            bool: True if an active client is available, False otherwise
        """
        return bool(self._active_client)

    @abstractmethod
    async def run(self, *args, **kwargs):
        """
        Abstract method for running operations with the active client.

        This method must be implemented by subclasses to define the specific
        operation logic for each type of manager.
        """
        pass

    def get_available_clients(self) -> List[T]:
        """
        Returns list of available client identifiers.

        Returns:
            List[str]: List of available client identifiers
        """
        return list(self._clients_map.values())

    def switch_active_client(self, client_id: str) -> bool:
        """
        Switches the active client to the specified one.

        Args:
            client_id (str): Identifier of the client to switch to

        Returns:
            bool: True if switch was successful, False otherwise
        """
        old_client_id = self._active_client_id
        self._set_active_client(client_id)
        return old_client_id != self._active_client_id

    async def close_connections(self) -> None:
        """
        Close all connections for currently available clients.
        """
        ...
