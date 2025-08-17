"""
Core receiver module for Octopus ANP communication.

This module provides ANP protocol receiver implementation, including:
- WebSocket client connection management
- ANPX protocol message handling
- ASGI application adapter
- Auto-reconnection mechanism
"""

# Protocol Components
# ASGI Adapter
from octopus.core.receiver.app_adapter import (
    ASGIAdapter,
    MockASGIApp,
    MockResponse,
)

# Message Handler
from octopus.core.receiver.message_handler import MessageHandler
from octopus.core.receiver.protocol import (
    ANPXDecoder,
    ANPXEncoder,
    ANPXMessage,
    HTTPMeta,
    MessageType,
    ResponseMeta,
    TLVTag,
)

# Connection Management
from octopus.core.receiver.reconnect import ConnectionState, ReconnectManager

# WebSocket Client (import service management classes from legacy anp_receiver.py)
try:
    from octopus.core.receiver.anp_receiver import (
        ANPReceiverService,
        DIDReceiverService,
        create_anp_receiver_service,
    )

    _HAS_ANP_RECEIVER = True
except ImportError:
    _HAS_ANP_RECEIVER = False

# WebSocket Client
from octopus.core.receiver.client import ReceiverClient

__all__ = [
    # Protocol Components
    "ANPXDecoder",
    "ANPXEncoder",
    "ANPXMessage",
    "HTTPMeta",
    "MessageType",
    "ResponseMeta",
    "TLVTag",
    # ASGI Adapter
    "ASGIAdapter",
    "MockASGIApp",
    "MockResponse",
    # Message Handler
    "MessageHandler",
    # Connection Management
    "ConnectionState",
    "ReconnectManager",
    # WebSocket Client
    "ReceiverClient",
]

# If anp_receiver module is available, add service management classes to export list
if _HAS_ANP_RECEIVER:
    __all__.extend([
        "ANPReceiverService",
        "DIDReceiverService",
        "create_anp_receiver_service",
    ])
