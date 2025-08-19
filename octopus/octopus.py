"""
FastAPI application main module.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import click
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .agents.message.message_agent import MessageAgent
from .api.ad_router import router as ad_router
from .api.auth_middleware import auth_middleware
from .api.chat_router import (
    router as chat_router,
    set_agents,
)
from .config.settings import get_settings, set_cli_overrides

# Import ANP Receiver Service
from .core.receiver.anp_receiver import (
    ANPReceiverService,
    create_anp_receiver_service,
)
from .master_agent import MasterAgent
from .utils.log_base import get_logger, setup_enhanced_logging

# Initialize enhanced logging
setup_enhanced_logging()

# Set default log level and get logger
settings = get_settings()
logger = get_logger(__name__)

# Global agents instances
master_agent = None
message_agent = None
text_processor_agent = None

# Global ANP Receiver Service instance
anp_receiver_service: ANPReceiverService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    global master_agent, message_agent, text_processor_agent, anp_receiver_service

    # Startup
    logger.info("Starting Octopus FastAPI application (main module)")

    try:
        # Initialize Message Agent
        logger.info("Initializing Message Agent...")
        message_agent = MessageAgent()
        logger.info("Message Agent initialized successfully")

        # Initialize Text Processor Agent
        logger.info("Initializing Text Processor Agent...")
        from octopus.agents.text_processor_agent import TextProcessorAgent

        text_processor_agent = TextProcessorAgent()
        logger.info("Text Processor Agent initialized successfully")

        # Initialize Master Agent
        logger.info("Initializing Master Agent...")
        master_agent = MasterAgent()
        master_agent.initialize()
        logger.info("Master Agent initialized successfully")

        # Inject agents into chat router
        set_agents(master_agent, message_agent)

        # Initialize ANP Receiver Service if enabled
        if settings.anp_sdk_enabled:
            logger.info("Initializing ANP Receiver Service...")
            logger.info(f"ANP Gateway WS URL: {settings.anp_gateway_ws_url}")
            logger.info(f"ANP Gateway HTTP URL: {settings.anp_gateway_http_url}")
            logger.info(f"Octopus running on port: {settings.port}")
            try:
                anp_receiver_service = await setup_anp_receiver_service(app)
                await anp_receiver_service.start()
                logger.info("ANP Receiver Service started successfully")
                # Log receiver service stats for debugging
                stats = anp_receiver_service.get_stats()
                logger.info(f"ANP Receiver Service stats: {stats}")
            except Exception as e:
                logger.error(f"Failed to start ANP Receiver Service: {str(e)}")
                # Don't fail the entire application if ANP service fails
        else:
            logger.info("ANP Receiver Service disabled by configuration")

        logger.info("All agents initialized successfully")
        logger.info("Application startup completed successfully")

    except Exception as e:
        logger.error(f"Failed to initialize agents: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Octopus FastAPI application")

    # Stop ANP Receiver Service
    if anp_receiver_service:
        try:
            logger.info("Stopping ANP Receiver Service...")
            await anp_receiver_service.stop()
            logger.info("ANP Receiver Service stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping ANP Receiver Service: {str(e)}")

    # Cleanup agents with error handling
    cleanup_tasks = [
        ("Master Agent", master_agent),
        ("Message Agent", message_agent),
        ("Text Processor Agent", text_processor_agent),
    ]

    for agent_name, agent in cleanup_tasks:
        if agent:
            try:
                if hasattr(agent, "cleanup"):
                    agent.cleanup()
                logger.info(f"{agent_name} cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up {agent_name}: {str(e)}")

    logger.info("Application shutdown completed")


async def setup_anp_receiver_service(app: FastAPI) -> ANPReceiverService:
    """Create and configure ANP Receiver Service with single DID support."""

    # Get ANP configuration from settings
    settings = get_settings()
    receiver_config = settings.anp_receiver

    # Use configured gateway URL
    gateway_url = settings.anp_gateway_ws_url or receiver_config.gateway_url

    # Create ANP Receiver Service
    service = await create_anp_receiver_service(
        app=app,
    )

    # Configure single DID service (no database lookup)
    if hasattr(settings, "did_document_path") and hasattr(
        settings, "did_private_key_path"
    ):
        if settings.did_document_path and settings.did_private_key_path:
            # Load DID from document
            import json

            try:
                with open(settings.did_document_path) as f:
                    did_document = json.load(f)
                did_id = did_document.get("id")
                if not did_id:
                    raise ValueError("DID document missing 'id' field")

                logger.info(f"Configuring DID service with {did_id}")

                await service.add_did_service(
                    did=did_id,
                    gateway_url=gateway_url,
                    did_document_path=settings.did_document_path,
                    private_key_path=settings.did_private_key_path,
                )
                logger.info(f"Successfully configured DID service: {did_id}")
            except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to load DID from document: {e}")
                logger.warning("Skipping DID service configuration")
        else:
            logger.warning("DID document or private key path not configured")
    else:
        logger.warning("DID configuration not found in settings")

    logger.info(
        "ANP Receiver Service configured",
        gateway_url=gateway_url,
        total_did_services=len(service.did_services),
    )

    return service


app = FastAPI(
    title=settings.app_name,
    description="A FastAPI application for the Octopus project",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

# Add authentication middleware
app.middleware("http")(auth_middleware)
logger.info("Authentication middleware added to FastAPI application")

# Mount static files
web_dir = os.path.join(os.path.dirname(__file__), "..", "web")
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")
    logger.info(f"Static files mounted from: {web_dir}")
else:
    logger.error(f"Web directory not found: {web_dir}")

# Include chat router
app.include_router(chat_router, prefix="/v1", tags=["chat"])

# Include agent description router
app.include_router(ad_router, tags=["agents"])


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main chat interface."""
    logger.info("Root endpoint accessed - serving chat interface")
    try:
        with open(os.path.join(web_dir, "index.html"), encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        logger.error("index.html not found in web directory")
        return HTMLResponse(
            content="<h1>Chat interface not found</h1><p>Please check web directory setup.</p>",
            status_code=404,
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.debug("Health check endpoint accessed")
    return {"status": "healthy"}


@app.get("/v1/info")
async def get_info():
    """Get application information."""
    logger.info("Application info endpoint accessed")
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "A FastAPI application for the Octopus project",
    }


@app.get("/anp/status")
async def get_anp_status():
    """Get ANP Receiver Service status."""
    global anp_receiver_service

    if not anp_receiver_service:
        return {
            "enabled": False,
            "status": "disabled",
            "message": "ANP Receiver Service is not enabled",
        }

    stats = anp_receiver_service.get_stats()
    return {
        "enabled": True,
        "status": "running" if anp_receiver_service.is_running() else "stopped",
        "stats": stats,
    }


def run_server() -> None:
    """Run the FastAPI application server."""
    import signal
    import sys

    import uvicorn

    # Get settings after CLI overrides are applied
    settings = get_settings()

    # Print startup banner
    print("\n" + "=" * 60)
    print(f"🐙 {settings.app_name} Multi-Agent AI System v{settings.app_version}")
    print("=" * 60)

    # Server configuration
    print(f"🌐 Server: http://{settings.host}:{settings.port}")
    print(f"🔧 Debug Mode: {'ON' if settings.debug else 'OFF'}")
    print(f"📝 Log Level: {settings.log_level}")

    # AI configuration
    print(f"🤖 AI Model: {settings.openai_model}")
    if (
        settings.openai_base_url
        and settings.openai_base_url != "https://api.openai.com/v1"
    ):
        print(f"🔗 AI Base URL: {settings.openai_base_url}")

    # ANP configuration
    if settings.anp_sdk_enabled:
        gateway_url = settings.anp_gateway_ws_url or settings.anp_receiver.gateway_url
        print("📡 ANP Status: ENABLED")
        print(f"   └─ Gateway: {gateway_url}")
        print(f"   └─ Local Port: {settings.anp_receiver.local_port}")
    else:
        print("📡 ANP Status: DISABLED")

    print("=" * 60 + "\n")

    # Log to file as well
    logger.info(f"🚀 Starting {settings.app_name} on {settings.host}:{settings.port}")
    logger.info(f"Debug: {settings.debug}, Log Level: {settings.log_level}")
    if settings.anp_sdk_enabled:
        logger.info(
            f"ANP enabled - Gateway: {gateway_url}, Local: {settings.anp_receiver.local_port}"
        )
    else:
        logger.info("ANP disabled")

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Run the FastAPI application
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
        )
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        sys.exit(1)
    finally:
        logger.info("Application shutdown complete")


@click.command()
@click.option(
    "--host",
    "-h",
    default=None,
    help="Host to bind the server to",
    show_default="0.0.0.0",
)
@click.option(
    "--port",
    "-p",
    type=int,
    default=None,
    help="Port to run the server on",
    show_default="9527",
)
@click.option(
    "--anp-gateway",
    default=None,
    help="ANP gateway WebSocket URL",
    show_default="anpproxy.com",
)
@click.option(
    "--debug/--no-debug",
    default=None,
    help="Enable/disable debug mode",
)
@click.option(
    "--anp/--no-anp",
    "anp_enabled",
    default=None,
    help="Enable/disable ANP receiver service",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default=None,
    help="Set logging level",
    show_default="INFO",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Custom environment file path",
)
@click.version_option(version="0.1.0", prog_name="Octopus")
def main(
    host: str | None = None,
    port: int | None = None,
    anp_port: int | None = None,
    anp_gateway: str | None = None,
    debug: bool | None = None,
    anp_enabled: bool | None = None,
    log_level: str | None = None,
    config: Path | None = None,
) -> None:
    """
    🐙 Octopus Multi-Agent AI System

    A FastAPI-based multi-agent AI system with ANP (Agent Network Protocol) support
    for distributed agent communication.

    \b
    📋 Quick Start Examples:
      # Start with default settings
      uv run python -m octopus.octopus

      # Run on custom port
      uv run python -m octopus.octopus --port 9529

      # Multiple instances with ANP
      uv run python -m octopus.octopus --port 9527 --anp-gateway www.anpproxy.com  # Instance A
      uv run python -m octopus.octopus --port 9529 --anp-gateway www.anpproxy.com  # Instance B

      # Debug mode
      uv run python -m octopus.octopus --debug --log-level DEBUG

      # Disable ANP for standalone mode
      uv run python -m octopus.octopus --no-anp

      # Use custom config file
      uv run python -m octopus.octopus --config .env.production

    \b
    🌐 Default Ports:
      • Main Server: 9527
      • ANP Gateway: www.anpproxy.com
    """
    try:
        # Handle custom config file
        if config:
            from dotenv import load_dotenv

            load_dotenv(config)
            click.echo(f"✅ Loaded configuration from: {config}")

        # Collect CLI overrides
        overrides = _collect_cli_overrides(
            host=host,
            port=port,
            anp_port=anp_port,
            anp_gateway=anp_gateway,
            debug=debug,
            anp_enabled=anp_enabled,
            log_level=log_level,
        )

        # Apply overrides if any
        if overrides:
            set_cli_overrides(**overrides)
            override_keys = [
                k for k in overrides.keys() if not k.startswith("anp_receiver")
            ]
            if override_keys:
                click.echo(f"🔧 CLI overrides applied: {', '.join(override_keys)}")

        # Run the server
        run_server()

    except Exception as e:
        click.echo(f"❌ Failed to start Octopus: {e}", err=True)
        raise click.ClickException(str(e))


def _collect_cli_overrides(**kwargs) -> dict:
    """Collect and prepare CLI overrides for settings."""
    from .config.settings import ReceiverConfig

    cli_overrides = {}
    anp_receiver_overrides = {}

    # Basic overrides
    for key, value in kwargs.items():
        if value is None:
            continue

        if key == "anp_port":
            anp_receiver_overrides["local_port"] = value
        elif key == "anp_gateway":
            cli_overrides["anp_gateway_ws_url"] = value
            anp_receiver_overrides["gateway_url"] = value
        elif key == "anp_enabled":
            cli_overrides["anp_sdk_enabled"] = value
        elif key in ["host", "port", "debug", "log_level"]:
            cli_overrides[key] = value

    # Create ANP receiver config if needed
    if anp_receiver_overrides:
        cli_overrides["anp_receiver"] = ReceiverConfig(**anp_receiver_overrides)

    return cli_overrides


if __name__ == "__main__":
    main()
