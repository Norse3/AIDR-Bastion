from app.managers.llm.clients.anthropic import AsyncAnthropicClient
from app.managers.llm.clients.azure_openai import AsyncAzureOpenAIClient
from app.managers.llm.clients.ollama import AsyncOllamaClient
from app.managers.llm.clients.openai import AsyncOpenAIClient


ALL_CLIENTS = [
    AsyncOpenAIClient,
    AsyncAnthropicClient,
    AsyncAzureOpenAIClient,
    AsyncOllamaClient,
]

ALL_CLIENTS_MAP = {
    client._identifier: client
    for client in ALL_CLIENTS
}
