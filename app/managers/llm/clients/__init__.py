from app.managers.llm.clients.openai import AsyncOpenAIClient


ALL_CLIENTS = [
    AsyncOpenAIClient,
]

ALL_CLIENTS_MAP = {
    client._identifier: client
    for client in ALL_CLIENTS
}
