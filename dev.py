"""
Development server script for the Octopus FastAPI application.
"""

import logging
import uvicorn
from utils.log_base import set_log_color_level

# Initialize logging
logger = set_log_color_level(level=logging.DEBUG, include_location=True, configure_all=True)

if __name__ == "__main__":
    logger.info("Starting development server for Octopus FastAPI application")
    logger.info("Development mode: hot reload enabled")
    logger.info("Server will be accessible at: http://0.0.0.0:8000")
    logger.info("API documentation will be available at: http://0.0.0.0:8000/docs")
    
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["./"],
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Development server stopped by user")
    except Exception as e:
        logger.error(f"Error starting development server: {e}")
        raise 