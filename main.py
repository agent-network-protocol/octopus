"""
FastAPI application main module.
"""

from fastapi import FastAPI

app = FastAPI(
    title="Octopus API",
    description="A FastAPI application for the Octopus project",
    version="0.1.0"
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Hello World from Octopus!"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/api/v1/info")
async def get_info():
    """Get application information."""
    return {
        "name": "Octopus",
        "version": "0.1.0",
        "description": "A FastAPI application for the Octopus project"
    } 