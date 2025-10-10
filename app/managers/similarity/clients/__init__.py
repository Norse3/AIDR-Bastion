from app.managers.similarity.clients.elasticsearch import AsyncElasticsearchClient
from app.managers.similarity.clients.opensearch import AsyncOpenSearchClient

ALL_CLIENTS = [AsyncOpenSearchClient, AsyncElasticsearchClient]

ALL_CLIENTS_MAP = {client._identifier: client for client in ALL_CLIENTS}
