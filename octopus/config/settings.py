"""
Application settings and configuration.
"""

from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

# ANP Default constants
DEFAULT_CHUNK_SIZE = 64 * 1024  # 64KB
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_KEEPALIVE_INTERVAL = 30.0
DEFAULT_PING_INTERVAL = 10.0
DEFAULT_RECONNECT_DELAY = 5.0
DEFAULT_MAX_RECONNECT_ATTEMPTS = 10


class TLSConfig(BaseModel):
    """TLS/SSL configuration."""

    enabled: bool = True
    cert_file: Path | None = None
    key_file: Path | None = None
    ca_file: Path | None = None
    verify_mode: str = "required"  # none, optional, required

    def __post_init__(self):
        if self.verify_mode not in ["none", "optional", "required"]:
            raise ValueError("verify_mode must be one of: none, optional, required")


class AuthConfig(BaseModel):
    """Authentication configuration."""

    enabled: bool = True
    shared_secret: str | None = None
    token_expiry: int = 3600  # seconds
    max_attempts: int = 3
    # DID-WBA sub-config
    did_wba_enabled: bool = False
    did: str | None = None
    did_document_path: Path | None = None
    private_key_path: Path | None = None
    resolver_base_url: str | None = None
    nonce_window_seconds: int = 300
    allowed_dids: list[str] = Field(default_factory=list)
    # JWT for DID-WBA (server-side issuance/verification)
    jwt_private_key_path: Path | None = None
    jwt_public_key_path: Path | None = None


class ReceiverConfig(BaseSettings):
    """Receiver-specific configuration."""

    # Gateway connection
    gateway_url: str = "ws://0.0.0.0:8789"  # WebSocket port 8789

    # Local app settings
    local_host: str = "127.0.0.1"
    local_port: int = 9527
    local_app_module: str | None = None  # e.g., "myapp:app"

    # Connection settings
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    keepalive_interval: float = DEFAULT_KEEPALIVE_INTERVAL
    ping_interval: float = DEFAULT_PING_INTERVAL

    # Reconnection
    reconnect_enabled: bool = True
    reconnect_delay: float = DEFAULT_RECONNECT_DELAY
    max_reconnect_attempts: int = DEFAULT_MAX_RECONNECT_ATTEMPTS

    # Security
    tls: TLSConfig = Field(default_factory=TLSConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)

    # Protocol settings
    chunk_size: int = DEFAULT_CHUNK_SIZE

    # Service advertising - dynamically determined by get_advertised_services()
    # No longer using static configuration

    model_config = {
        "env_prefix": "ANP__RECEIVER__",
        "env_nested_delimiter": "__",
        "case_sensitive": False,
    }


class Settings(BaseSettings):
    """Application settings."""

    # APPLICATION CONFIGURATION

    app_name: str = "Octopus"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 9527

    # LOGGING CONFIGURATION

    log_level: str = "INFO"
    log_file: str | None = None
    log_file_path: str = "~/Library/Logs/octopus/octopus.log"
    default_file_encoding: str = "utf-8"

    # PATH CONFIGURATION

    did_document_path: str | None = None
    did_private_key_path: str | None = None

    # AGENT CONFIGURATION

    max_agents: int = 100
    agent_timeout: int = 300  # seconds

    # ANP (Agent Network Protocol) CONFIGURATION

    anp_sdk_enabled: bool = True
    anp_receiver: ReceiverConfig = Field(default_factory=ReceiverConfig)

    # ANP Gateway Configuration
    anp_gateway_url: str = "ws://localhost:8789"
    anp_gateway_http_port: int = 8089

    # ANP Protocol Settings
    anp_max_message_size: int = 10485760  # 10MB
    anp_max_chunk_size: int = 1048576  # 1MB
    anp_max_pending_chunks: int = 1000
    anp_max_request_id_length: int = 100

    # ANP Timeouts
    anp_auth_timeout: float = 30.0
    anp_chunk_timeout: float = 60.0
    anp_request_timeout: float = 300.0

    # DID (Decentralized Identity) CONFIGURATION
    did_domain: str = "didhost.cc"
    did_path: str = "test:public"
    auth_nonce_expiry_minutes: int = 5
    auth_timestamp_expiry_minutes: int = 5

    # OPENAI CONFIGURATION
    model_provider: str = "openai"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str | None = None

    openai_temperature: float | None = None
    openai_max_tokens: int | None = None

    # JWT AUTHENTICATION
    jwt_algorithm: str | None = None
    access_token_expire_minutes: int | None = None
    jwt_private_key_path: str | None = None
    jwt_public_key_path: str | None = None

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "env_nested_delimiter": "__",
        "case_sensitive": False,
        "extra": "allow",
    }


def get_advertised_services() -> list[str]:
    """
    Get basic service capabilities that this receiver can handle.

    Returns:
        List of service path patterns this receiver supports
    """
    # Basic service capabilities - Gateway will map DID services to these capabilities
    return [
        "agents",  # Agent routes (jsonrpc, info, etc.)
        "v1",  # Chat and API routes
        "",  # Root path for main interface
        "anp/status",  # ANP status endpoint
    ]


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
