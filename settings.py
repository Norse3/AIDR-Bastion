import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class BaseSearchSettings(BaseModel):
    """
    Base class for search system settings.

    Provides common configuration structure for Elasticsearch and OpenSearch clients.
    """

    user: Optional[str] = None
    password: Optional[str] = None
    host: str
    port: int
    scheme: str = "https"
    pool_size: int = 10

    def get_common_config(self) -> dict:
        """
        Returns common configuration parameters for all search clients.

        Returns:
            dict: Common configuration dictionary
        """
        config = {
            "hosts": [f"{self.scheme}://{self.host}:{self.port}"],
            "verify_certs": False,
            "ssl_show_warn": False,
            "retry_on_status": (500, 502, 503, 504),
            "max_retries": 3,
        }

        if self.user and self.password:
            config["basic_auth"] = (self.user, self.password)

        return config


class OpenSearchSettings(BaseSearchSettings):
    def get_client_config(self) -> dict:
        return {
            **self.get_common_config(),
            "pool_maxsize": self.pool_size,
        }


class ElasticsearchSettings(BaseSearchSettings):
    def get_client_config(self) -> dict:
        config = {
            "hosts": [f"{self.scheme}://{self.host}:{self.port}"],
        }

        # Add authentication only if both user and password are provided
        if self.user and self.password:
            config["basic_auth"] = (self.user, self.password)

        return config


class QdrantSettings(BaseModel):
    """
    Configuration settings for Qdrant vector database.

    Qdrant is a specialized vector search engine optimized for similarity search.
    """

    host: str
    port: int = 6333
    grpc_port: Optional[int] = 6334
    api_key: Optional[str] = None
    prefer_grpc: bool = False
    timeout: int = 30

    def get_client_config(self) -> dict:
        """
        Returns configuration parameters for Qdrant client.

        Returns:
            dict: Qdrant client configuration dictionary
        """
        config = {
            "host": self.host,
            "port": self.port,
            "timeout": self.timeout,
            "prefer_grpc": self.prefer_grpc,
        }

        if self.grpc_port:
            config["grpc_port"] = self.grpc_port

        if self.api_key:
            config["api_key"] = self.api_key

        return config


class KafkaSettings(BaseModel):
    bootstrap_servers: str
    topic: str
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None
    save_prompt: bool = False


def _load_version() -> str:
    """
    Load version from VERSION file.

    Returns:
        str: Version string from VERSION file, or "unknown" if file not found
    """
    version_path = Path("VERSION")
    if not version_path.exists():
        return "unknown"

    try:
        with open(version_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"Error reading VERSION file: {e}")
        return "unknown"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AIDR Bastion"
    VERSION: str = Field(default_factory=lambda: _load_version())

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    OS: Optional[OpenSearchSettings] = None
    ES: Optional[ElasticsearchSettings] = None
    QDRANT: Optional[QdrantSettings] = None
    KAFKA: Optional[KafkaSettings] = None
    PIPELINE_CONFIG: dict = Field(default_factory=dict)

    SIMILARITY_PROMPT_INDEX: str = "similarity-prompt-index"
    SIMILARITY_DEFAULT_CLIENT: str = Field(default="opensearch", description="Default client for similarity search")

    SIMILARITY_NOTIFY_THRESHOLD: float = 0.7
    SIMILARITY_BLOCK_THRESHOLD: float = 0.87

    CORS_ORIGINS: list[str] = Field(default=["*"], env="CORS_ORIGINS", description="List of allowed origins for CORS")

    EMBEDDINGS_MODEL: Optional[str] = Field(
        default="nomic-ai/nomic-embed-text-v1.5", description="Model for embeddings"
    )

    LLM_DEFAULT_CLIENT: Optional[str] = Field(default="litellm", description="Default client for LLM")

    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = Field(default="", description="API key for OpenAI ChatGPT API")
    OPENAI_MODEL: Optional[str] = Field(default="gpt-4", description="Default model for OpenAI ChatGPT API")
    OPENAI_BASE_URL: Optional[str] = Field(
        default="https://api.openai.com/v1", description="Default base URL for OpenAI ChatGPT API"
    )

    # Anthropic Configuration
    ANTHROPIC_API_KEY: Optional[str] = Field(default="", description="API key for Anthropic Claude API")
    ANTHROPIC_MODEL: Optional[str] = Field(
        default="claude-sonnet-4-5-20250929", description="Default model for Anthropic Claude API"
    )
    ANTHROPIC_BASE_URL: Optional[str] = Field(
        default="https://api.anthropic.com", description="Default base URL for Anthropic Claude API"
    )

    # Azure OpenAI Configuration
    AZURE_OPENAI_ENDPOINT: Optional[str] = Field(default="", description="Azure OpenAI endpoint URL")
    AZURE_OPENAI_API_KEY: Optional[str] = Field(default="", description="Azure OpenAI API key")
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = Field(
        default="gpt-4", description="Azure OpenAI deployment/model name"
    )
    AZURE_OPENAI_API_VERSION: Optional[str] = Field(
        default="2024-02-15-preview", description="Azure OpenAI API version"
    )

    # Ollama Configuration
    OLLAMA_BASE_URL: Optional[str] = Field(
        default="http://localhost:11434", description="Ollama API base URL (using official Ollama library)"
    )
    OLLAMA_MODEL: Optional[str] = Field(default="llama3", description="Ollama model name")
    
    # LiteLLM Configuration
    LITELLM_BASE_URL: Optional[str] = Field(
        default="http://localhost:32539", description="LiteLLM Proxy Router base URL"
    )
    LITELLM_MODEL: Optional[str] = Field(default="llama3", description="LiteLLM model route name")

    # LLM Common Configuration
    LLM_TEMPERATURE: float = Field(default=0.1, description="Temperature for LLM responses (0.0-2.0)")
    LLM_MAX_TOKENS: int = Field(default=1000, description="Maximum tokens for LLM responses")

    ML_MODEL_PATH: Optional[str] = None


def load_pipeline_config() -> dict:
    """
    Loads pipeline configuration from config.json file.
    Returns raw configuration without instantiating pipelines to avoid circular imports.
    """
    config_path = Path("config.json")
    loaded_config = {}

    if not config_path.exists():
        return loaded_config

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Error reading config.json: {e}")
        return loaded_config


@lru_cache()
def get_settings() -> Settings:
    """
    Returns cached instance of settings.
    Used to avoid reading .env file multiple times.
    """
    settings = Settings()
    settings.PIPELINE_CONFIG = load_pipeline_config()
    return settings
