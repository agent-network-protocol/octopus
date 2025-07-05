"""
FastAPI application main module.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from octopus.utils.log_base import setup_enhanced_logging
from octopus.config.settings import get_settings

# Initialize logging using setup_enhanced_logging at the main entry point
settings = get_settings()
logger = setup_enhanced_logging(level=getattr(logging, settings.log_level))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Octopus FastAPI application (main module)")
    logger.info("Application startup completed successfully")
    yield
    # Shutdown
    logger.info("Shutting down Octopus FastAPI application")


app = FastAPI(
    title=settings.app_name,
    description="A FastAPI application for the Octopus project",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint."""
    logger.info("Root endpoint accessed")
    return {"message": "Hello World from Octopus!"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.debug("Health check endpoint accessed")
    return {"status": "healthy"}


@app.get("/api/v1/info")
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
        "octopus.octopus:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main() 