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
    title="Octopus API",
    description="A FastAPI application for the Octopus project",
    version=settings.app_version,
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
    
    logger.info("Starting Octopus FastAPI server on port 9880")
    
    # Run the FastAPI application
    uvicorn.run(
        "octopus.octopus:app",
        host="0.0.0.0",
        port=9880,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main() 