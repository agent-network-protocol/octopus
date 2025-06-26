"""
Development server script for the Octopus FastAPI application.
"""

import logging
import sys
import os
import uvicorn

# Add the parent directory to the Python path so we can import octopus modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from octopus.utils.log_base import set_log_color_level

# Initialize logging
logger = set_log_color_level(level=logging.DEBUG, include_location=True, configure_all=True)

if __name__ == "__main__":
    logger.info("Starting development server for Octopus FastAPI application")
    logger.info("Development mode: hot reload enabled")
    logger.info("Server will be accessible at: http://0.0.0.0:8000")
    logger.info("API documentation will be available at: http://0.0.0.0:8000/docs")
    
    try:
        uvicorn.run(
            "octopus.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["./octopus"],
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Development server stopped by user")
    except Exception as e:
        logger.error(f"Error starting development server: {e}")
        raise 