from app.managers.similarity.clients.elasticsearch import AsyncElasticsearchClient
from app.managers.similarity.clients.opensearch import AsyncOpenSearchClient
from app.managers.similarity.clients.qdrant import AsyncQdrantClientWrapper

ALL_CLIENTS = [AsyncOpenSearchClient, AsyncElasticsearchClient, AsyncQdrantClientWrapper]

ALL_CLIENTS_MAP = {client._identifier: client for client in ALL_CLIENTS}
