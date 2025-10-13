from app.managers.llm.clients.anthropic import AsyncAnthropicClient
from app.managers.llm.clients.openai import AsyncOpenAIClient


ALL_CLIENTS = [
    AsyncOpenAIClient,
    AsyncAnthropicClient,
]

ALL_CLIENTS_MAP = {
    client._identifier: client
    for client in ALL_CLIENTS
}
