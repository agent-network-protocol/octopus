"""
Application settings and configuration.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "Octopus"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 9527

    # Logging
    log_level: str = "INFO"
    log_file: str | None = None

    # Agent settings
    max_agents: int = 100
    agent_timeout: int = 300  # seconds

    # ANP SDK settings
    anp_sdk_enabled: bool = True

    # Model Provider settings
    model_provider: str = "openai"  # Only supports "openai"

    # OpenAI settings
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str | None = None
    openai_deployment: str | None = None
    openai_api_version: str | None = None
    openai_temperature: float | None = None
    openai_max_tokens: int | None = None

    # DID Authentication settings
    did_document_path: str = "did.json"
    did_private_key_path: str = "key-1_private.pem"

    # DID Authentication server settings
    nonce_expiration_minutes: int = 5
    timestamp_expiration_minutes: int = 5
    did_documents_path: str = "did_keys"
    did_document_filename: str = "did.json"
    local_port: int = 8000

    # JWT settings
    jwt_algorithm: str | None = None
    access_token_expire_minutes: int | None = None
    jwt_private_key_path: str | None = None
    jwt_public_key_path: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
