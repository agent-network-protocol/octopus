"""
WebSocket Client - 主WebSocket客户端，负责连接管理和消息分发

这个模块实现了与 ANP Gateway 的 WebSocket 连接管理，
包括认证、心跳、消息处理和自动重连功能。
"""

import asyncio
import importlib
import json
import signal
import socket
import time
from typing import Any

import websockets
from agent_connect.authentication import DIDWbaAuthHeader
from websockets.client import WebSocketClientProtocol

from octopus.config.settings import AuthConfig, ReceiverConfig, get_settings
from octopus.core.receiver.app_adapter import ASGIAdapter, MockASGIApp
from octopus.core.receiver.message_handler import MessageHandler
from octopus.core.receiver.reconnect import ConnectionState, ReconnectManager
from octopus.utils.log_base import get_logger

logger = get_logger(__name__)


def build_auth_headers(
    auth_config: AuthConfig, gateway_url: str = ""
) -> dict[str, str]:
    """Build DID-WBA Authorization headers for a given ws(s) URL."""

    if not auth_config.enabled:
        return {}

    # Get DID paths from main settings if not in auth_config
    settings = get_settings()

    did_doc_path = auth_config.did_document_path or settings.did_document_path
    private_key_path = auth_config.private_key_path or settings.did_private_key_path

    if not did_doc_path or not private_key_path:
        logger.warning(
            "Missing DID document or private key path for DID-WBA client header generation"
        )
        return {}

    try:
        client = DIDWbaAuthHeader(
            did_document_path=str(did_doc_path),
            private_key_path=str(private_key_path),
        )

        # Adjust gateway URL based on operating system
        original_url = gateway_url
        adjusted_gateway_url = _adjust_gateway_url_for_os(gateway_url)
        logger.info("Original gateway URL: %s", original_url)
        logger.info("Adjusted gateway URL for authentication: %s", adjusted_gateway_url)

        headers = client.get_auth_header(adjusted_gateway_url)
        # Ensure proper case for websockets extra_headers
        normalized = {
            k if isinstance(k, str) else str(k): v if isinstance(v, str) else str(v)
            for k, v in headers.items()
        }
        return normalized

    except ImportError:
        logger.warning("agent_connect not available, DID-WBA authentication disabled")
        return {}
    except Exception as exc:
        logger.error("Failed to build auth headers", error=str(exc))
        return {}


def _adjust_gateway_url_for_os(gateway_url: str) -> str:
    """Adjust gateway URL based on operating system and domain override settings."""
    import os

    # Get settings to check for domain override
    system = os.name.lower()
    if system == "posix":  # macOS, Linux, etc.
        # For all POSIX systems, keep localhost for local development
        if "localhost" in gateway_url:
            logger.info("Keeping localhost for local development")
            return gateway_url
    # For other systems (Windows), keep as is
    return gateway_url


def find_free_port(host: str = "127.0.0.1", start_port: int = 8000) -> int:
    """Find a free port starting from start_port."""
    port = start_port
    while port < 65535:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
                return port
        except OSError:
            port += 1

    raise RuntimeError(f"No free port found starting from {start_port}")


def parse_module_attr(module_string: str) -> tuple[str, str]:
    """Parse module:attribute string."""
    if ":" not in module_string:
        raise ValueError("Module string must be in format 'module:attribute'")

    module_name, attr_name = module_string.split(":", 1)
    return module_name.strip(), attr_name.strip()


async def import_app(module_string: str) -> Any:
    """Dynamically import an ASGI application."""
    module_name, attr_name = parse_module_attr(module_string)

    try:
        module = importlib.import_module(module_name)
        app = getattr(module, attr_name)

        logger.info(f"Successfully imported app from {module_string}")
        return app

    except ImportError as e:
        logger.error(f"Failed to import module {module_name}: {e}")
        raise
    except AttributeError as e:
        logger.error(f"Failed to get attribute {attr_name} from {module_name}: {e}")
        raise


class GracefulShutdown:
    """Context manager for graceful shutdown handling."""

    def __init__(self) -> None:
        self.shutdown_event = asyncio.Event()
        self.tasks: list[asyncio.Task] = []

    def __enter__(self) -> "GracefulShutdown":
        # Register signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._signal_handler)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        # Restore default signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, signal.SIG_DFL)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.shutdown_event.set()

    def add_task(self, task: asyncio.Task) -> None:
        """Add a task to be cancelled on shutdown."""
        self.tasks.append(task)

    async def wait(self) -> None:
        """Wait for shutdown signal."""
        await self.shutdown_event.wait()

    async def cleanup(self) -> None:
        """Cancel all tracked tasks."""
        if self.tasks:
            logger.info(f"Cancelling {len(self.tasks)} tasks")

            for task in self.tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete cancellation
            if self.tasks:
                await asyncio.gather(*self.tasks, return_exceptions=True)


class ReceiverClient:
    """WebSocket client that connects to Gateway and serves local ASGI app."""

    def __init__(self, config: ReceiverConfig, app: Any | None = None) -> None:
        self.config = config

        # WebSocket connection
        self.websocket: WebSocketClientProtocol | None = None
        self.connected = False

        # Application adapter
        self.app = app
        self.asgi_adapter: ASGIAdapter | None = None

        # Message handling
        self.message_handler: MessageHandler | None = None

        # Reconnection management
        self.reconnect_manager = ReconnectManager(config)
        self.reconnect_manager.set_connect_callback(self._connect_websocket)
        self.reconnect_manager.set_state_change_callback(self._on_state_change)

        # Tasks
        self._message_task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None

        logger.info(f"Receiver client initialized, gateway_url={config.gateway_url}")

    async def start(self) -> None:
        """Start the receiver client."""
        try:
            # Load ASGI app if not provided
            if self.app is None:
                await self._load_app()

            # Initialize ASGI adapter
            base_url = f"http://{self.config.local_host}:{self.config.local_port}"
            self.asgi_adapter = ASGIAdapter(self.app, base_url)

            # Initialize message handler
            self.message_handler = MessageHandler(
                self.asgi_adapter, self.config.chunk_size
            )
            self.message_handler.set_send_callback(self._send_message)

            # Connect to gateway
            success = await self.reconnect_manager.connect()
            if not success:
                raise RuntimeError("Failed to connect to gateway")

            logger.info("Receiver client started successfully")

        except Exception as e:
            logger.error(f"Failed to start receiver client, error={str(e)}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the receiver client."""
        logger.info("Stopping receiver client")

        # Set connected to False first to stop loops
        self.connected = False

        # Close WebSocket connection first
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("WebSocket connection closed")
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
            finally:
                self.websocket = None

        # Stop reconnection
        await self.reconnect_manager.disconnect()

        # Cancel tasks with timeout
        tasks_to_cancel = [self._message_task, self._ping_task]
        tasks_to_cancel = [task for task in tasks_to_cancel if task and not task.done()]
        
        if tasks_to_cancel:
            logger.info(f"Cancelling {len(tasks_to_cancel)} tasks")
            for task in tasks_to_cancel:
                task.cancel()
            
            try:
                # Wait for tasks to complete cancellation with timeout
                await asyncio.wait_for(
                    asyncio.gather(*tasks_to_cancel, return_exceptions=True),
                    timeout=5.0
                )
                logger.info("All tasks cancelled successfully")
            except asyncio.TimeoutError:
                logger.warning("Task cancellation timed out, some tasks may still be running")
            except Exception as e:
                logger.warning(f"Error during task cancellation: {e}")

        self._message_task = None
        self._ping_task = None
        logger.info("Receiver client stopped")

    async def run(self) -> None:
        """Run the receiver client with graceful shutdown."""
        with GracefulShutdown() as shutdown:
            try:
                await self.start()
                # Add tasks to shutdown manager for proper cleanup
                if self._message_task:
                    shutdown.add_task(self._message_task)
                if self._ping_task:
                    shutdown.add_task(self._ping_task)
                
                await shutdown.wait()
                logger.info("Shutdown signal received, cleaning up...")
            finally:
                # Ensure cleanup happens
                await shutdown.cleanup()
                await self.stop()

    async def _load_app(self) -> None:
        """Load ASGI app from configuration."""
        if self.config.local_app_module:
            self.app = await import_app(self.config.local_app_module)
        else:
            self.app = MockASGIApp()
            logger.info("Using mock ASGI app")

    async def _connect_websocket(self) -> bool:
        """Connect to WebSocket gateway."""
        try:
            # Build headers
            headers = {}
            if self.config.auth and self.config.auth.enabled:
                headers.update(
                    build_auth_headers(self.config.auth, self.config.gateway_url)
                )

            # Connect
            self.websocket = await websockets.connect(
                self.config.gateway_url,
                extra_headers=headers,
                ping_interval=self.config.keepalive_interval,
                ping_timeout=self.config.timeout_seconds,
                close_timeout=self.config.timeout_seconds,
            )

            self.connected = True

            # Send connection ready notification
            await self._send_connection_ready()

            # Start tasks with error handling
            self._message_task = asyncio.create_task(self._handle_messages())
            self._ping_task = asyncio.create_task(self._ping_loop())

            # Add task completion callbacks for debugging
            self._message_task.add_done_callback(self._on_message_task_done)
            self._ping_task.add_done_callback(self._on_ping_task_done)

            logger.info(
                "🟢 [CLIENT] WebSocket connected, message and ping tasks started"
            )
            return True

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            self.websocket = None
            self.connected = False
            return False

    async def _send_connection_ready(self) -> None:
        """Send connection ready notification to gateway."""
        if not self.websocket:
            return

        try:
            # Just notify gateway that connection is ready for service discovery
            ready_message = {
                "type": "connection_ready",
                "timestamp": int(time.time()),
                "connection_id": id(self),  # Use object id as connection identifier
            }

            logger.info("🔵 [CONNECTION] Notifying gateway that connection is ready")
            await self.websocket.send(json.dumps(ready_message))
            logger.info("🟢 [CONNECTION] Connection ready notification sent")

        except Exception as e:
            logger.error(
                f"Failed to send connection ready notification, error={str(e)}"
            )

    async def _handle_messages(self) -> None:
        """Handle incoming WebSocket messages."""
        try:
            async for message in self.websocket:
                logger.debug(
                    f"🔍 [MSG_RECEIVE] Received message type: {type(message)}, size: {len(message) if hasattr(message, '__len__') else 'unknown'}"
                )

                if isinstance(message, bytes):
                    logger.info(
                        f"🔄 [MSG_RECEIVE] Processing ANPX binary message, size: {len(message)}"
                    )
                    if self.message_handler:
                        try:
                            await self.message_handler.handle_message(message)
                            logger.info(
                                "🟢 [MSG_RECEIVE] Message processed successfully"
                            )
                        except Exception as handler_error:
                            logger.error(
                                f"🔴 [MSG_RECEIVE] Message handler failed: {handler_error}",
                                exc_info=True,
                            )
                    else:
                        logger.error("🔴 [MSG_RECEIVE] No message handler configured!")
                elif isinstance(message, str):
                    logger.info("🔄 [MSG_RECEIVE] Processing JSON control message")
                    # Handle JSON control messages from gateway
                    await self._handle_gateway_command(message)
                else:
                    logger.warning(
                        f"🟡 [MSG_RECEIVE] Unknown message type: {type(message)}"
                    )
        except websockets.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error handling messages: {e}")
        finally:
            self.connected = False

    async def _ping_loop(self) -> None:
        try:
            while self.connected and self.websocket:
                await asyncio.sleep(self.config.ping_interval)
                if self.websocket and self.connected:
                    try:
                        pong_waiter = await self.websocket.ping()
                        await asyncio.wait_for(pong_waiter, timeout=10.0)
                        logger.debug("Ping/pong successful")
                    except TimeoutError:
                        logger.warning("Ping timeout, connection may be unstable")
                    except websockets.ConnectionClosed:
                        logger.info("Connection closed during ping")
                        break
                    except Exception as ping_error:
                        logger.error(f"Ping failed: {ping_error}")
                        break
        except asyncio.CancelledError:
            logger.debug("Ping loop cancelled")
        except Exception as e:
            logger.error(f"Ping loop error: {e}")
        finally:
            self.connected = False

    def _send_message(self, message) -> None:
        """Send message through WebSocket (callback for message handler)."""
        if self.websocket and self.connected:
            try:
                # Handle ANP Proxy message format directly

                frame_data = message.encode()
                asyncio.create_task(self._send_frame(frame_data))
                logger.debug(
                    f"🟢 [SEND] ANP Proxy message sent, size: {len(frame_data)}"
                )

            except Exception as e:
                logger.error(f"🔴 [SEND] Message encoding failed: {e}")
                raise

    async def _send_frame(self, frame: bytes) -> None:
        """Send a single frame."""
        try:
            if self.websocket:
                await self.websocket.send(frame)
        except Exception as e:
            logger.error(f"Failed to send frame: {e}")

    async def _handle_gateway_command(self, message: str) -> None:
        """Handle gateway command messages."""
        try:
            logger.debug(
                "🔍 [RECEIVER] Raw gateway message received",
                message_length=len(message),
            )
            logger.debug(
                "🔍 [RECEIVER] Message content",
                message=message[:500] + "..." if len(message) > 500 else message,
            )

            data = json.loads(message)
            command_type = data.get("type")

            logger.info(f"🔄 [RECEIVER] Gateway command received: {command_type}")
            logger.debug("🔍 [RECEIVER] Full command data", command_data=data)

            if command_type == "service_capability_request":
                await self._respond_service_capabilities(data)
            elif command_type == "health_check_request":
                await self._respond_health_status(data)
            elif command_type == "service_assignment":
                await self._acknowledge_service_assignment(data)
            else:
                logger.warning(f"Unknown gateway command type: {command_type}")
                logger.debug(
                    "🔍 [RECEIVER] Unknown command details",
                    command_type=command_type,
                    available_fields=list(data.keys()),
                )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse gateway command JSON: {e}")
            logger.debug("🔍 [RECEIVER] Invalid JSON message", message=message[:200])
        except Exception as e:
            logger.error(f"Error handling gateway command: {e}")
            logger.debug(
                "🔍 [RECEIVER] Exception details",
                exception_type=type(e).__name__,
                message=str(e),
            )

    async def _respond_service_capabilities(self, request: dict) -> None:
        """Respond to service capability request from gateway."""
        try:
            from octopus.config.settings import get_advertised_services

            advertised_services = get_advertised_services()

            response = {
                "type": "service_capability_response",
                "request_id": request.get("request_id"),
                "timestamp": int(time.time()),
                "capabilities": {
                    "supported_services": advertised_services,
                    "max_concurrent_requests": 100,
                    "supports_http": True,
                    "supports_websocket": True,
                    "health_check_available": True,
                },
            }

            logger.info(
                f"🔄 [RECEIVER] Sending service capabilities: {advertised_services}"
            )
            await self.websocket.send(json.dumps(response))

        except Exception as e:
            logger.error(f"Failed to respond to service capability request: {e}")

    async def _respond_health_status(self, request: dict) -> None:
        """Respond to health check request from gateway."""
        try:
            response = {
                "type": "health_check_response",
                "request_id": request.get("request_id"),
                "timestamp": int(time.time()),
                "status": "healthy",
                "details": {
                    "connected": self.connected,
                    "app_running": self.app is not None,
                    "asgi_adapter_ready": self.asgi_adapter is not None,
                },
            }

            logger.info("🔄 [RECEIVER] Sending health status: healthy")
            await self.websocket.send(json.dumps(response))

        except Exception as e:
            logger.error(f"Failed to respond to health check: {e}")

    async def _acknowledge_service_assignment(self, assignment: dict) -> None:
        """Acknowledge service assignment from gateway."""
        try:
            assigned_services = assignment.get("assigned_services", [])

            response = {
                "type": "service_assignment_ack",
                "request_id": assignment.get("request_id"),
                "timestamp": int(time.time()),
                "status": "accepted",
                "assigned_services": assigned_services,
            }

            logger.info(
                f"🔄 [RECEIVER] Acknowledging service assignment: {assigned_services}"
            )
            await self.websocket.send(json.dumps(response))

        except Exception as e:
            logger.error(f"Failed to acknowledge service assignment: {e}")

    def _on_message_task_done(self, task: asyncio.Task) -> None:
        """Handle message task completion."""
        if task.cancelled():
            logger.info("🔵 [CLIENT] Message task was cancelled")
        elif task.exception():
            logger.error(f"🔴 [CLIENT] Message task failed: {task.exception()}")
        else:
            logger.info("🟢 [CLIENT] Message task completed normally")

    def _on_ping_task_done(self, task: asyncio.Task) -> None:
        """Handle ping task completion."""
        if task.cancelled():
            logger.info("🔵 [CLIENT] Ping task was cancelled")
        elif task.exception():
            logger.error(f"🔴 [CLIENT] Ping task failed: {task.exception()}")
        else:
            logger.info("🟢 [CLIENT] Ping task completed normally")

    def _on_state_change(self, new_state: ConnectionState) -> None:
        """Handle connection state changes."""
        logger.info(f"Connection state changed to: {new_state}")
