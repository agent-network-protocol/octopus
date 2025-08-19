"""
Reconnection Manager - 提供自动重连和指数退避机制
"""

import asyncio
import time
from collections.abc import Callable
from enum import Enum
from typing import Any

from octopus.config.settings import ReceiverConfig
from octopus.utils.log_base import get_logger

logger = get_logger(__name__)


class ConnectionState(Enum):
    """Connection states for reconnection manager."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class ReconnectManager:
    """Manages automatic reconnection with exponential backoff."""

    def __init__(self, config: ReceiverConfig) -> None:
        """
        Initialize reconnect manager.

        Args:
            config: Receiver configuration
        """
        self.config = config
        self.state = ConnectionState.DISCONNECTED
        self.current_attempt = 0
        self.last_connected_time: float | None = None
        self.reconnect_task: asyncio.Task | None = None
        self.connect_callback: Callable | None = None
        self.state_change_callback: Callable | None = None

        logger.info(
            f"Reconnect manager initialized, enabled={config.reconnect_enabled}"
        )

    def set_connect_callback(self, callback: Callable) -> None:
        """Set callback function for connection attempts."""
        self.connect_callback = callback

    def set_state_change_callback(
        self, callback: Callable[[ConnectionState], None]
    ) -> None:
        """Set callback for state changes."""
        self.state_change_callback = callback

    def _set_state(self, new_state: ConnectionState) -> None:
        """Change connection state and notify callback."""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state

            logger.info(
                f"Connection state changed, old_state={old_state.value}, new_state={new_state.value}"
            )

            if self.state_change_callback:
                try:
                    self.state_change_callback(new_state)
                except Exception as e:
                    logger.error(f"Error in state change callback, error={str(e)}")

    async def connect(self) -> bool:
        """
        Attempt initial connection.

        Returns:
            True if connection successful, False otherwise
        """
        if self.state in [ConnectionState.CONNECTING, ConnectionState.CONNECTED]:
            return self.state == ConnectionState.CONNECTED

        self._set_state(ConnectionState.CONNECTING)
        self.current_attempt = 1

        try:
            if self.connect_callback:
                success = await self.connect_callback()
                if success:
                    self._set_state(ConnectionState.CONNECTED)
                    self.current_attempt = 0
                    self.last_connected_time = time.time()
                    return True
                else:
                    self._set_state(ConnectionState.DISCONNECTED)
                    return False
            else:
                logger.error("No connect callback set")
                self._set_state(ConnectionState.FAILED)
                return False

        except Exception as e:
            logger.error(f"Connection attempt failed, error={str(e)}")
            self._set_state(ConnectionState.DISCONNECTED)
            return False

    def on_connection_lost(self) -> None:
        """Handle connection loss."""
        if self.state == ConnectionState.CONNECTED:
            logger.warning("Connection lost")
            self._set_state(ConnectionState.DISCONNECTED)

            if self.config.reconnect_enabled:
                self._start_reconnect()

    def on_connection_error(self, error: Exception) -> None:
        """Handle connection error."""
        logger.error(f"Connection error, error={str(error)}")

        if self.state != ConnectionState.FAILED:
            self._set_state(ConnectionState.DISCONNECTED)

            if self.config.reconnect_enabled:
                self._start_reconnect()

    def _start_reconnect(self) -> None:
        """Start reconnection process."""
        if self.reconnect_task and not self.reconnect_task.done():
            return  # Already reconnecting

        if self.current_attempt >= self.config.max_reconnect_attempts:
            logger.error(
                f"Maximum reconnection attempts reached, max_attempts={self.config.max_reconnect_attempts}"
            )
            self._set_state(ConnectionState.FAILED)
            return

        self._set_state(ConnectionState.RECONNECTING)
        self.reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Reconnection loop with exponential backoff."""
        while (
            self.config.reconnect_enabled
            and self.current_attempt < self.config.max_reconnect_attempts
            and self.state == ConnectionState.RECONNECTING
        ):
            self.current_attempt += 1

            # Calculate delay with exponential backoff
            delay = min(
                self.config.reconnect_delay * (2 ** (self.current_attempt - 1)),
                300,  # Cap at 5 minutes
            )

            logger.info(
                f"Attempting reconnection, attempt={self.current_attempt}, max_attempts={self.config.max_reconnect_attempts}, delay={delay:.1f}s"
            )

            await asyncio.sleep(delay)

            # Check if we should still reconnect
            if self.state != ConnectionState.RECONNECTING:
                break

            # Attempt connection
            try:
                if self.connect_callback:
                    success = await self.connect_callback()
                    if success:
                        self._set_state(ConnectionState.CONNECTED)
                        self.current_attempt = 0
                        self.last_connected_time = time.time()

                        logger.info(
                            f"Reconnection successful, attempt={self.current_attempt}, total_time={time.time() - (self.last_connected_time or 0):.1f}s"
                        )
                        return
                    else:
                        logger.warning("Reconnection attempt failed")

            except Exception as e:
                logger.error(f"Reconnection attempt error, error={str(e)}")

        # Max attempts reached or reconnection disabled
        if self.current_attempt >= self.config.max_reconnect_attempts:
            logger.error("All reconnection attempts failed")
            self._set_state(ConnectionState.FAILED)
        else:
            self._set_state(ConnectionState.DISCONNECTED)

    async def disconnect(self) -> None:
        """Manually disconnect and stop reconnection."""
        logger.info("Manual disconnect requested")

        # Cancel reconnection task with timeout
        if self.reconnect_task and not self.reconnect_task.done():
            self.reconnect_task.cancel()
            try:
                await asyncio.wait_for(self.reconnect_task, timeout=3.0)
            except asyncio.CancelledError:
                logger.info("Reconnect task cancelled successfully")
            except asyncio.TimeoutError:
                logger.warning("Reconnect task cancellation timed out")
            except Exception as e:
                logger.warning(f"Error cancelling reconnect task: {e}")
            finally:
                self.reconnect_task = None

        self._set_state(ConnectionState.DISCONNECTED)
        self.current_attempt = 0

    def force_reconnect(self) -> None:
        """Force immediate reconnection attempt."""
        if self.state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            return

        logger.info("Forcing reconnection")
        self.current_attempt = 0
        self._start_reconnect()

    def get_stats(self) -> dict[str, Any]:
        """Get reconnection statistics."""
        uptime = None
        if self.last_connected_time and self.state == ConnectionState.CONNECTED:
            uptime = time.time() - self.last_connected_time

        return {
            "state": self.state.value,
            "current_attempt": self.current_attempt,
            "max_attempts": self.config.max_reconnect_attempts,
            "reconnect_enabled": self.config.reconnect_enabled,
            "uptime_seconds": uptime,
            "last_connected_time": self.last_connected_time,
        }
