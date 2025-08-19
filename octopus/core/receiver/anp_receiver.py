"""
ANP Receiver - Unified ANP receiving service management and WebSocket client
"""

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from ...config.settings import AuthConfig, ReceiverConfig, get_settings

# ANP utilities are now embedded
from ...utils.log_base import get_logger
from .client import ReceiverClient

logger = get_logger(__name__)


# ============================================================================
# Authentication
# ============================================================================


@dataclass
class DidAuthResult:
    success: bool
    did: str | None = None
    error: str | None = None
    details: dict[str, Any] | None = None


def _normalize_headers(raw_headers: Any) -> dict[str, str]:
    """Normalize websockets headers (HeadersLike) to lowercase dict[str,str]."""
    try:
        return {k.lower(): v for k, v in raw_headers.items()}  # type: ignore[attr-defined]
    except Exception:
        result: dict[str, str] = {}
        for item in raw_headers:  # type: ignore[assignment]
            try:
                k, v = item
                result[str(k).lower()] = str(v)
            except Exception:
                pass
        return result


class DidWbaVerifierAdapter:
    """Adapter for DID-WBA verification in Octopus receiver."""

    def __init__(self, config: AuthConfig):
        self.config = config
        self._verifier = None

        # Try to initialize agent_connect verifier if available
        try:
            from octopus.anp_sdk.anp_auth.did_wba_verifier import (
                DidWbaVerifier as SdkDidWbaVerifier,
                DidWbaVerifierConfig,
            )

            # Load optional JWT keys for SDK verifier
            jwt_private = None
            jwt_public = None
            try:
                if self.config.jwt_private_key_path:
                    jwt_private = str(self.config.jwt_private_key_path.read_text())
                if self.config.jwt_public_key_path:
                    jwt_public = str(self.config.jwt_public_key_path.read_text())
            except Exception:
                jwt_private = None
                jwt_public = None

            # Get main settings for domain override configuration
            get_settings()

            self._verifier = SdkDidWbaVerifier(
                DidWbaVerifierConfig(
                    jwt_private_key=jwt_private,
                    jwt_public_key=jwt_public,
                )
            )
        except ImportError:
            logger.warning(
                "ANP SDK DID-WBA verifier not available, verification will be disabled"
            )

    async def verify(self, headers_like: Any, domain: str) -> DidAuthResult:
        if not self.config.enabled:
            return DidAuthResult(success=False, error="DID-WBA disabled")

        if not self._verifier:
            return DidAuthResult(success=False, error="DID-WBA verifier not available")

        headers = _normalize_headers(headers_like)
        authorization = headers.get("authorization")
        if not authorization:
            return DidAuthResult(success=False, error="Missing Authorization header")

        try:
            # Use SDK verifier if available
            result = await self._verifier.verify_auth_header(authorization, domain)
            did = result.get("did")
            if self.config.allowed_dids and did not in set(self.config.allowed_dids):
                return DidAuthResult(success=False, error="DID not allowed")
            return DidAuthResult(success=True, did=did)

        except Exception as exc:
            logger.error("DID-WBA verification error", error=str(exc))
            return DidAuthResult(success=False, error=str(exc))


# Use the adapter directly
DidWbaVerifier = DidWbaVerifierAdapter


# ============================================================================
# Configuration Models
# ============================================================================


class ANPReceiverSettings(BaseModel):
    """ANP Receiver Settings configuration."""

    receiver: ReceiverConfig


# ============================================================================
# Service Manager
# ============================================================================


class DIDReceiverService:
    """Individual DID Receiver Service."""

    def __init__(
        self,
        did: str,
        fastapi_app: FastAPI,
        gateway_url: str,
        did_document_path: str | None = None,
        private_key_path: str | None = None,
    ):
        self.did = did
        self.fastapi_app = fastapi_app
        self.gateway_url = gateway_url
        self.did_document_path = did_document_path
        self.private_key_path = private_key_path
        self.receiver_client: ReceiverClient | None = None
        self._running = False

        logger.info(
            f"DID Receiver Service initialized for {did}",
            gateway_url=gateway_url,
        )

    async def start(self) -> None:
        """Start the DID Receiver Service."""
        if self._running:
            logger.warning(f"DID Receiver Service for {self.did} is already running")
            return

        try:
            logger.info(f"Starting DID Receiver Service for {self.did}...")

            # Create receiver configuration
            app_settings = get_settings()
            receiver_config = ReceiverConfig(
                gateway_url=self.gateway_url,
                local_host="127.0.0.1",
                local_port=app_settings.port,
            )

            # Configure authentication if DID credentials are provided
            if self.did_document_path and self.private_key_path:
                from pathlib import Path

                auth_config = AuthConfig(
                    enabled=True,
                    did_wba_enabled=True,
                    did_document_path=Path(self.did_document_path),
                    private_key_path=Path(self.private_key_path),
                )
                receiver_config.auth = auth_config
                logger.info(f"DID authentication configured for {self.did}")

            # Create receiver client
            self.receiver_client = ReceiverClient(
                config=receiver_config,
                app=self.fastapi_app,
            )

            # Start receiver client
            await self.receiver_client.start()
            self._running = True

            logger.info(f"DID Receiver Service for {self.did} started successfully")

        except Exception as e:
            self._running = False
            logger.error(
                f"Failed to start DID Receiver Service for {self.did}: {str(e)}"
            )
            raise

    async def stop(self) -> None:
        """Stop the DID Receiver Service."""
        logger.info(f"Stopping DID Receiver Service for {self.did}...")

        if self.receiver_client:
            try:
                await self.receiver_client.stop()
            except Exception as e:
                logger.error(f"Error stopping receiver client for {self.did}: {str(e)}")

        self._running = False
        logger.info(f"DID Receiver Service for {self.did} stopped successfully")

    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        return {
            "did": self.did,
            "running": self._running,
            "gateway_url": self.gateway_url,
        }


class ANPReceiverService:
    """Multi-DID ANP Receiver Service manager."""

    def __init__(
        self,
        fastapi_app: FastAPI,
        config: ReceiverConfig,
        gateway_url: str,
    ):
        self.fastapi_app = fastapi_app
        self.config = config
        self.gateway_url = gateway_url
        self.did_services: dict[str, DIDReceiverService] = {}
        self._running = False

        logger.info(
            "ANP Receiver Service initialized",
            gateway_url=gateway_url,
        )

    async def add_did_service(
        self,
        did: str,
        gateway_url: str | None = None,
        did_document_path: str | None = None,
        private_key_path: str | None = None,
        auto_start: bool = True,
    ) -> DIDReceiverService:
        """Add a DID receiver service."""
        if did in self.did_services:
            raise ValueError(f"DID service for '{did}' already exists")

        # Use defaults if not provided
        gateway_url = gateway_url or self.gateway_url

        # Create DID service
        did_service = DIDReceiverService(
            did=did,
            fastapi_app=self.fastapi_app,
            gateway_url=gateway_url,
            did_document_path=did_document_path,
            private_key_path=private_key_path,
        )

        self.did_services[did] = did_service

        if auto_start and self._running:
            await did_service.start()

        logger.info(f"Added DID Receiver Service: {did}")
        return did_service

    async def start(self) -> None:
        """Start the ANP Receiver Service and all DID services."""
        if self._running:
            logger.warning("ANP Receiver Service is already running")
            return

        try:
            self._running = True

            # Start all DID services
            for did, did_service in self.did_services.items():
                try:
                    await did_service.start()
                    logger.info(f"Started DID service: {did}")
                except Exception as e:
                    logger.error(f"Failed to start DID service '{did}': {str(e)}")

            logger.info("ANP Receiver Service started successfully")

        except Exception as e:
            self._running = False
            logger.error(f"Failed to start ANP Receiver Service: {str(e)}")
            raise

    async def stop(self) -> None:
        """Stop the ANP Receiver Service and all DID services."""
        logger.info("Stopping ANP Receiver Service")

        # Stop all DID services
        for did, did_service in self.did_services.items():
            try:
                await did_service.stop()
                logger.info(f"Stopped DID service: {did}")
            except Exception as e:
                logger.error(f"Error stopping DID service '{did}': {str(e)}")

        self._running = False
        logger.info("ANP Receiver Service stopped")

    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running

    def get_did_service(self, did: str) -> DIDReceiverService | None:
        """Get a specific DID service by DID."""
        return self.did_services.get(did)

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        stats = {
            "running": self._running,
            "total_did_services": len(self.did_services),
            "running_did_services": sum(
                1 for s in self.did_services.values() if s.is_running()
            ),
            "did_services": {},
        }

        for did, did_service in self.did_services.items():
            stats["did_services"][did] = did_service.get_stats()

        return stats


# ============================================================================
# Factory Functions
# ============================================================================


async def create_anp_receiver_service(
    app: FastAPI,
    did_configs: list[dict[str, Any]] | None = None,
) -> ANPReceiverService:
    """Create an ANP Receiver Service with multiple DID configurations."""

    # Get ANP configuration from settings
    settings = get_settings()
    receiver_config = settings.anp_receiver

    # Use configured gateway URL
    gateway_url = settings.anp_gateway_ws_url or receiver_config.gateway_url

    # TODO(anpproxy): Gateway should push database proxy paths to receiver via WSS.
    # Receiver will validate its local app endpoints and acknowledge usable paths.

    # Create ANP Receiver Service
    service = ANPReceiverService(
        fastapi_app=app,
        config=receiver_config,
        gateway_url=gateway_url,
    )

    # Add DID services if provided
    if did_configs:
        for did_config in did_configs:
            await service.add_did_service(
                did=did_config["did"],
                gateway_url=did_config.get("gateway_url"),
                did_document_path=did_config.get("did_document_path"),
                private_key_path=did_config.get("private_key_path"),
                auto_start=False,
            )

    return service
