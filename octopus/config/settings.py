"""
Application settings and configuration.
"""

import logging
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "Octopus"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Agent settings
    max_agents: int = 100
    agent_timeout: int = 300  # seconds
    
    # ANP SDK settings
    anp_sdk_enabled: bool = True
    
    # Model Provider settings
    model_provider: str = "openai"  # Currently only supports "openai"
    
    # OpenAI settings
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: Optional[str] = None
    openai_deployment: Optional[str] = None
    openai_api_version: Optional[str] = None
    openai_temperature: Optional[float] = None
    openai_max_tokens: Optional[int] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Get application settings."""
    return Settings() 