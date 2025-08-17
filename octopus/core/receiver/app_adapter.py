"""
ASGI Application Adapter - Handle HTTP request integration with ASGI applications

This module provides an adapter layer between ANPX protocol messages and ASGI applications,
supporting conversion of ANPX HTTP requests to ASGI format and executing application logic.
"""

import logging
from typing import Any

from octopus.core.receiver.protocol import ANPXMessage, HTTPMeta

logger = logging.getLogger(__name__)


class MockResponse:
    """Mock response object for ASGI processing."""

    def __init__(self, status_code: int, headers: dict[str, str], content: bytes):
        self.status_code = status_code
        self.headers = headers
        self.content = content
        self.reason_phrase = self._get_reason_phrase(status_code)

    def _get_reason_phrase(self, status_code: int) -> str:
        """Get HTTP reason phrase for status code."""
        reasons = {
            200: "OK",
            201: "Created",
            202: "Accepted",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
        }
        return reasons.get(status_code, "Unknown")


class ASGIAdapter:
    """Adapter for calling ASGI applications from ANPX messages."""

    def __init__(self, app: Any, base_url: str = "http://localhost") -> None:
        """
        Initialize ASGI adapter.

        Args:
            app: The ASGI application to adapt
            base_url: Base URL for the application
        """
        self.app = app
        self.base_url = base_url
        logger.info(f"ASGI adapter initialized with base_url: {base_url}")

    async def process_request(self, message: ANPXMessage) -> MockResponse:
        """
        Process ANPX message through ASGI app and return response.

        Args:
            message: ANPX message containing HTTP request data

        Returns:
            MockResponse: Response object containing status, headers, and body
        """
        http_meta = message.get_http_meta()
        if not http_meta:
            return MockResponse(400, {}, b"Bad Request: Missing HTTP metadata")

        try:
            # Build ASGI scope from HTTP metadata
            http_body = message.get_http_body()
            scope = self._build_asgi_scope(http_meta, http_body or b"")

            # Collect response data
            response_data = {"status": 200, "headers": [], "body": b""}

            async def receive():
                """ASGI receive callable."""
                return {
                    "type": "http.request",
                    "body": http_body or b"",
                    "more_body": False,
                }

            async def send(asgi_message):
                """ASGI send callable."""
                if asgi_message["type"] == "http.response.start":
                    response_data["status"] = asgi_message["status"]
                    response_data["headers"] = asgi_message.get("headers", [])
                elif asgi_message["type"] == "http.response.body":
                    response_data["body"] += asgi_message.get("body", b"")

            # Execute ASGI application
            await self.app(scope, receive, send)

            # Convert headers to dict format
            headers = {
                name.decode() if isinstance(name, bytes) else str(name): value.decode()
                if isinstance(value, bytes)
                else str(value)
                for name, value in response_data["headers"]
            }

            return MockResponse(response_data["status"], headers, response_data["body"])

        except Exception as e:
            logger.error(f"ASGI processing error: {e}", exc_info=True)
            error_msg = f"Internal Server Error: {str(e)}"
            return MockResponse(500, {}, error_msg.encode())

    def _build_asgi_scope(self, http_meta: HTTPMeta, body: bytes) -> dict[str, Any]:
        """
        Build ASGI HTTP scope from HTTP metadata.

        Args:
            http_meta: HTTP request metadata
            body: Request body bytes

        Returns:
            dict: ASGI scope dictionary
        """
        # Parse URL components
        path = http_meta.path
        if not path.startswith("/"):
            path = "/" + path

        # Build query string from query parameters
        query_string = "&".join(f"{k}={v}" for k, v in http_meta.query.items()).encode(
            "utf-8"
        )

        # Convert headers to ASGI format (list of 2-tuples of byte strings)
        headers = [
            (name.lower().encode("latin1"), value.encode("latin1"))
            for name, value in http_meta.headers.items()
        ]

        # Add content-length header if not present and body exists
        if body and not any(name.lower() == b"content-length" for name, _ in headers):
            headers.append((b"content-length", str(len(body)).encode("latin1")))

        # Build ASGI scope
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.1"},
            "http_version": "1.1",
            "method": http_meta.method.upper(),
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": query_string,
            "root_path": "",
            "scheme": "http",
            "server": ("localhost", 80),
            "client": ("127.0.0.1", 0),
            "headers": headers,
        }

        return scope


class MockASGIApp:
    """Mock ASGI application for testing purposes."""

    async def __call__(self, scope, receive, send):
        """
        Mock ASGI application callable.

        Args:
            scope: ASGI scope dictionary
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] == "http":
            # Send response start
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"x-powered-by", b"octopus-anp-receiver"),
                ],
            })

            # Build response body
            response_data = {
                "message": "Mock ASGI response from Octopus ANP Receiver",
                "method": scope.get("method", "UNKNOWN"),
                "path": scope.get("path", "/"),
                "query": scope.get("query_string", b"").decode("utf-8"),
                "headers_count": len(scope.get("headers", [])),
            }

            # Send response body
            await send({
                "type": "http.response.body",
                "body": str(response_data).replace("'", '"').encode("utf-8"),
                "more_body": False,
            })

        else:
            # Unsupported scope type
            await send({
                "type": "http.response.start",
                "status": 400,
                "headers": [(b"content-type", b"text/plain")],
            })
            await send({
                "type": "http.response.body",
                "body": b"Unsupported ASGI scope type",
                "more_body": False,
            })


__all__ = ["ASGIAdapter", "MockASGIApp", "MockResponse"]
