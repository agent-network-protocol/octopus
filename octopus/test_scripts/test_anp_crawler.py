"""
Test ANP Crawler functionality with DID authentication.
This test verifies that the ANP crawler can successfully access the local /ad.json endpoint
using DID authentication.
"""

import asyncio
import logging
from pathlib import Path

from octopus.anp_sdk.anp_crawler.anp_crawler import ANPCrawler
from octopus.config.settings import get_settings
from octopus.utils.log_base import setup_enhanced_logging


class ANPCrawlerTest:
    """Test class for ANP Crawler functionality."""

    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)

    async def wait_for_server(
        self, host: str = "localhost", port: int = None, max_wait: int = 30
    ) -> bool:
        """
        Wait for the FastAPI server to be ready.

        Args:
            host: Server host
            port: Server port
            max_wait: Maximum wait time in seconds

        Returns:
            bool: True if server is ready, False if timeout
        """
        if port is None:
            port = self.settings.port

        import aiohttp

        url = f"http://{host}:{port}/health"
        self.logger.info(f"Waiting for server to be ready at {url}")

        for i in range(max_wait):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            self.logger.info(f"Server is ready after {i+1} seconds")
                            return True
            except Exception as e:
                self.logger.debug(f"Server not ready yet (attempt {i+1}): {e}")

            await asyncio.sleep(1)

        self.logger.error(f"Server not ready after {max_wait} seconds")
        return False

    def get_did_paths(self) -> tuple[str, str]:
        """
        Get DID document and private key paths.

        Returns:
            tuple: (did_document_path, private_key_path)
        """
        # Get DID paths from settings or environment or use defaults
        did_document_path = self.settings.did_document_path or str(
            Path(__file__).parent.parent.parent / "docs/user_public/did.json"
        )
        private_key_path = self.settings.did_private_key_path or str(
            Path(__file__).parent.parent.parent / "docs/user_public/key-1_private.pem"
        )

        self.logger.info(f"Using DID document: {did_document_path}")
        self.logger.info(f"Using private key: {private_key_path}")

        # Verify files exist
        if not Path(did_document_path).exists():
            raise FileNotFoundError(f"DID document not found: {did_document_path}")
        if not Path(private_key_path).exists():
            raise FileNotFoundError(f"Private key file not found: {private_key_path}")

        return did_document_path, private_key_path

    async def test_local_ad_json_access(self) -> bool:
        """
        Test accessing the local /ad.json endpoint using ANP crawler.

        Returns:
            bool: True if test passed, False otherwise
        """
        try:
            self.logger.info("Starting local /ad.json access test using ANP crawler")

            # Construct local URL
            local_url = f"http://localhost:{self.settings.port}/ad.json"
            self.logger.info(f"Testing access to: {local_url}")

            # Get DID paths for authentication
            try:
                did_document_path, private_key_path = self.get_did_paths()
            except FileNotFoundError as e:
                self.logger.warning(f"⚠️ DID files not found: {e}")
                # Use None values, ANP crawler will handle gracefully
                did_document_path, private_key_path = None, None

            # Use ANP crawler to test local endpoint access
            test_task = "Test accessing the local agent description file to verify server connectivity and authentication"

            # TODO: Update to use new ANPCrawler class interface
            # For now, create a basic crawler instance and test connectivity
            crawler = ANPCrawler(
                did_document_path=did_document_path,
                private_key_path=private_key_path,
                cache_enabled=True,
            )

            # Test basic connectivity using fetch_auto method
            try:
                result_data, interfaces = await crawler.fetch_auto(local_url)
                result = {
                    "status": "success",
                    "data": result_data,
                    "interfaces": interfaces,
                    "task": test_task,
                }
            except Exception as e:
                result = {"status": "error", "error": str(e), "task": test_task}

            # Check ANP crawler results
            if result.get("type") == "error":
                self.logger.error(
                    f"❌ ANP Crawler test failed: {result.get('content')}"
                )
                return False

            # Verify results
            visited_urls = result.get("visited_urls", [])
            crawled_documents = result.get("crawled_documents", [])

            self.logger.info(f"Crawl completed - visited {len(visited_urls)} URLs")
            self.logger.info(f"Crawled {len(crawled_documents)} documents")

            if local_url in visited_urls:
                self.logger.info("✅ Successfully accessed local /ad.json endpoint")

                # Check if we got valid content
                for doc in crawled_documents:
                    if doc.get("url") == local_url:
                        content = doc.get("content", {})
                        if isinstance(content, dict) and content.get("name"):
                            self.logger.info(
                                f"✅ Retrieved valid agent description: {content.get('name')}"
                            )
                            return True
                        break

                self.logger.info("✅ URL accessed successfully")
                return True
            else:
                self.logger.error(f"❌ Target URL {local_url} was not accessed")
                return False

        except Exception as e:
            self.logger.error(f"Test failed with exception: {str(e)}")
            import traceback

            self.logger.error(traceback.format_exc())
            return False

    async def run_full_test(self, wait_for_server: bool = True) -> bool:
        """
        Run the complete ANP Crawler test.

        Args:
            wait_for_server: Whether to wait for server to be ready

        Returns:
            bool: True if all tests passed, False otherwise
        """
        self.logger.info("🚀 Starting ANP Crawler integration test")

        try:
            # Wait for server if requested
            if wait_for_server:
                if not await self.wait_for_server():
                    self.logger.error("❌ Server startup timeout - cannot run test")
                    return False

            # Add a small delay to ensure server is fully ready
            await asyncio.sleep(2)

            # Run the main test
            test_result = await self.test_local_ad_json_access()

            if test_result:
                self.logger.info("🎉 ANP Crawler integration test PASSED")
            else:
                self.logger.error("💥 ANP Crawler integration test FAILED")

            return test_result

        except Exception as e:
            self.logger.error(f"Test suite failed: {str(e)}")
            return False


async def run_anp_crawler_test(wait_for_server: bool = True) -> bool:
    """
    Entry point for running ANP Crawler tests.

    Args:
        wait_for_server: Whether to wait for server to be ready

    Returns:
        bool: True if tests passed, False otherwise
    """
    # Initialize logging for this test
    logger = logging.getLogger("anp_crawler_test")

    try:
        # Create and run test
        test_instance = ANPCrawlerTest()
        return await test_instance.run_full_test(wait_for_server=wait_for_server)

    except Exception as e:
        logger.error(f"Failed to run ANP Crawler test: {str(e)}")
        return False


async def run_anp_crawler_integration_test():
    """
    Run ANP Crawler integration test after server startup.
    This function runs in the background to test DID authentication and crawler functionality.
    """
    import logging

    logger = logging.getLogger("anp_crawler_integration")

    try:
        logger.info("🔄 Starting ANP Crawler integration test (background task)")

        # Wait a bit more to ensure server is fully ready
        await asyncio.sleep(5)

        # Run the test
        test_result = await run_anp_crawler_test(wait_for_server=True)

        if test_result:
            logger.info("🎉 ANP Crawler integration test completed successfully!")
        else:
            logger.error("💥 ANP Crawler integration test failed!")

    except Exception as e:
        logger.error(f"ANP Crawler integration test error: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())


async def main():
    """Main function for standalone testing."""
    # Setup logging
    setup_enhanced_logging(level=logging.INFO)

    # Run the test
    success = await run_anp_crawler_test(wait_for_server=True)

    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Tests failed!")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
