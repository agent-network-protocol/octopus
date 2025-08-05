"""
ANP Fetch Tool - Simple wrapper for ANP Crawler fetch_text method
"""

import logging
from typing import Dict, Any, Tuple

from octopus.utils.log_base import setup_enhanced_logging
from octopus.anp_sdk.anp_crawler.anp_crawler import ANPCrawler
from octopus.config.settings import get_settings

# Initialize enhanced logging
setup_enhanced_logging()
logger = logging.getLogger(__name__)


async def anp_fetch_text_content(url: str) -> Tuple[Dict, list]:
    """
    Fetch text content from a URL using ANP protocol.
    
    Args:
        url: The URL to fetch content from
        
    Returns:
        tuple: (content_json, interfaces_list) - same as ANPCrawler.fetch_text()
    """
    logger.info(f"Fetching content from URL: {url}")
    
    # Get settings
    settings = get_settings()
    
    # Create ANPCrawler instance
    crawler = ANPCrawler(
        did_document_path=settings.did_document_path,
        private_key_path=settings.did_private_key_path,
        cache_enabled=True
    )
    
    # Call fetch_text and return the result
    return await crawler.fetch_text(url)