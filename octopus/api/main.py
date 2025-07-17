"""
Main FastAPI application for Octopus Agent API.
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from octopus.config.settings import get_settings
from octopus.utils.log_base import setup_enhanced_logging
from octopus.api.ad_router import router as ad_router
from octopus.api.agent_loader import initialize_agents


# Initialize enhanced logging
setup_enhanced_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Initialize all agents
initialize_agents()

# Create FastAPI app
app = FastAPI(
    title="Octopus Agent API",
    description="Multi-agent system with natural language interface",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ad_router, prefix="/api", tags=["agents"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Octopus Multi-Agent System API",
        "endpoints": {
            "agents_description": "/api/agents/ad.json",
            "jsonrpc": "/api/agents/jsonrpc",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}

if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} API server...")
    uvicorn.run(
        "octopus.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 