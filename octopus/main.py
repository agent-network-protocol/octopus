"""
FastAPI application main module.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from octopus.utils.log_base import set_log_color_level
from octopus.config.settings import get_settings

# Initialize logging and settings
settings = get_settings()
logger = set_log_color_level(level=getattr(logging, settings.log_level), include_location=True, configure_all=True)


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