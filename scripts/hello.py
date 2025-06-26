"""
FastAPI application entry point.
"""

import logging
import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI

# Add the parent directory to the Python path so we can import octopus modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from octopus.utils.log_base import set_log_color_level

# Initialize logging
logger = set_log_color_level(level=logging.INFO, include_location=True, configure_all=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Octopus FastAPI application")
    logger.info("Application startup completed successfully")
    yield
    # Shutdown
    logger.info("Shutting down Octopus FastAPI application")


app = FastAPI(
    title="Octopus API",
    description="A FastAPI application for the Octopus project",
    version="0.1.0",
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

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
