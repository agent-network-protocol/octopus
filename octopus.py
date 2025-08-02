"""
FastAPI application main module.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from octopus.utils.log_base import setup_enhanced_logging
from octopus.config.settings import get_settings
from octopus.master_agent import MasterAgent
from octopus.agents.message_agent.message_agent import MessageAgent
from octopus.api.chat_router import router as chat_router, set_agents
from octopus.api.ad_router import router as ad_router
from octopus.anp_sdk.anp_auth.auth_middleware import auth_middleware

# Import ANP Crawler test functionality
import asyncio
from octopus.test_scripts.test_anp_crawler import run_anp_crawler_integration_test

# Initialize logging using setup_enhanced_logging at the main entry point
settings = get_settings()
logger = setup_enhanced_logging(level=getattr(logging, settings.log_level))

# Global agents instances
master_agent = None
message_agent = None
text_processor_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    global master_agent, message_agent, text_processor_agent
    
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
        
        logger.info("All agents initialized successfully")
        logger.info("Application startup completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize agents: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Octopus FastAPI application")
    
    if master_agent:
        master_agent.cleanup()
        logger.info("Master Agent cleaned up")
    
    if message_agent:
        message_agent.cleanup() 
        logger.info("Message Agent cleaned up")
    
    if text_processor_agent:
        text_processor_agent.cleanup()
        logger.info("Text Processor Agent cleaned up")


app = FastAPI(
    title=settings.app_name,
    description="A FastAPI application for the Octopus project",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Add authentication middleware
app.middleware("http")(auth_middleware)
logger.info("Authentication middleware added to FastAPI application")

# Mount static files
app.mount("/static", StaticFiles(directory="web"), name="static")

# Include chat router
app.include_router(chat_router, prefix="/v1", tags=["chat"])

# Include agent description router
app.include_router(ad_router, tags=["agents"])


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main chat interface."""
    logger.info("Root endpoint accessed - serving chat interface")
    try:
        with open("web/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        logger.error("index.html not found in web directory")
        return HTMLResponse(
            content="<h1>Chat interface not found</h1><p>Please check web directory setup.</p>", 
            status_code=404
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
        "description": "A FastAPI application for the Octopus project"
    }


def main():
    """Main function to run the FastAPI application."""
    import uvicorn
    
    logger.info(f"Starting {settings.app_name} FastAPI server on {settings.host}:{settings.port}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"OpenAI Model: {settings.openai_model}")
    if settings.openai_base_url:
        logger.info(f"OpenAI Base URL: {settings.openai_base_url}")
    
    # Run the FastAPI application
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main() 