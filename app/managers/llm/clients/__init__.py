from app.managers.llm.clients.anthropic import AsyncAnthropicClient
from app.managers.llm.clients.azure_openai import AsyncAzureOpenAIClient
from app.managers.llm.clients.openai import AsyncOpenAIClient


ALL_CLIENTS = [
    AsyncOpenAIClient,
    AsyncAnthropicClient,
    AsyncAzureOpenAIClient,
]

ALL_CLIENTS_MAP = {
    client._identifier: client
    for client in ALL_CLIENTS
}
