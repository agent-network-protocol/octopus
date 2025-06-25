"""
FastAPI application entry point.
"""

import logging
from fastapi import FastAPI
from utils.log_base import set_log_color_level

# Initialize logging
logger = set_log_color_level(level=logging.INFO, include_location=True, configure_all=True)

app = FastAPI(
    title="Octopus API",
    description="A FastAPI application for the Octopus project",
    version="0.1.0"
)

@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info("Starting Octopus FastAPI application")
    logger.info("Application startup completed successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown."""
    logger.info("Shutting down Octopus FastAPI application")

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
