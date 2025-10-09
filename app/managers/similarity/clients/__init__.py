from app.managers.similarity.clients.elasticsearch import AsyncElasticSearchClient
from app.managers.similarity.clients.opensearch import AsyncOpenSearchClient


ALL_CLIENTS = [
    AsyncOpenSearchClient, 
    AsyncElasticSearchClient
]

ALL_CLIENTS_MAP = {
    client._identifier: client
    for client in ALL_CLIENTS
}
