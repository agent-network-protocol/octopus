"""
ANPX Message Handler - 负责协议解码和消息路由

这个模块处理 ANPX 协议消息的解码、缓冲和路由，
将接收到的二进制数据转换为结构化消息并分发处理。
"""

# Import correct protocol structures from ANP Proxy
import json
import struct
from collections.abc import Callable
from typing import Any

from octopus.core.receiver.app_adapter import ASGIAdapter
from octopus.core.receiver.protocol import (
    ANPXDecoder,
    ANPXEncoder,
    ANPXHeader,
    ANPXMessage,
    MessageType,
    TLVTag,
)
from octopus.utils.log_base import get_logger

logger = get_logger(__name__)

# Protocol constants
ANPX_HEADER_SIZE = 24
MAX_BUFFER_SIZE = 1024 * 1024  # 1MB buffer limit


class MessageHandler:
    """ANPX消息处理器 - 处理协议解析和ASGI路由"""

    def __init__(self, asgi_adapter: ASGIAdapter, chunk_size: int = 64 * 1024) -> None:
        """
        Initialize message handler.

        Args:
            asgi_adapter: ASGI adapter for processing HTTP requests
            chunk_size: Maximum chunk size for message encoding
        """
        self.asgi_adapter = asgi_adapter
        self.decoder = ANPXDecoder()
        self.encoder = ANPXEncoder(chunk_size)
        self.send_callback: Callable[[ANPXMessage], None] | None = None
        self.message_buffer = b""

        # Note: Chunking is now handled at decoder level, not here

        logger.info("Message handler initialized")

    def set_send_callback(self, callback: Callable[[Any], None]) -> None:
        """Set callback for sending messages back to gateway."""
        self.send_callback = callback

    def _decode_anp_proxy_message(self, data: bytes):
        """Decode ANPX message using local protocol implementation."""
        try:
            # Import local protocol structures
            from .protocol import ANPXDecoder

            if len(data) < 24:
                logger.debug(f"🔍 [DECODE] Message too short: {len(data)} < 24")
                return None

            # Use the local decoder
            decoder = ANPXDecoder()
            message = decoder.decode_message(data)

            if message:
                logger.debug(
                    "🔍 [DECODE] Successfully decoded message",
                    message_type=message.header.message_type,
                    request_id=message.get_request_id(),
                )
                return message
            else:
                logger.debug("🔍 [DECODE] Decoder returned None (chunked message?)")
                return None

        except Exception as e:
            logger.debug(f"🔍 [DECODE] Failed to decode message: {e}")
            return None

    async def handle_message(self, message_data: bytes) -> None:
        """
        Handle incoming ANPX message with buffering support.

        Args:
            message_data: Raw bytes received from WebSocket
        """
        try:
            logger.info(
                f"🔵 [MSG_HANDLER] Starting message handling, incoming size: {len(message_data)}"
            )

            # Add to buffer
            self.message_buffer += message_data
            logger.info(
                f"🔍 [MSG_HANDLER] Added {len(message_data)} bytes to buffer, "
                f"total buffer size: {len(self.message_buffer)}"
            )
            logger.info(
                f"🔍 [MSG_HANDLER] Raw message data: {message_data[:100].hex()}"
            )

            # Process complete messages from buffer
            while len(self.message_buffer) >= ANPX_HEADER_SIZE:
                logger.debug(
                    f"🔍 [MSG_HANDLER] Processing buffer, size: {len(self.message_buffer)}"
                )
                logger.debug(
                    f"🔍 [MSG_HANDLER] Buffer header: {self.message_buffer[:24].hex()}"
                )

                # Decode message directly using ANP Proxy protocol
                logger.info(
                    "🔍 [MSG_HANDLER] Attempting to decode ANP Proxy message from buffer"
                )
                message = self._decode_anp_proxy_message(self.message_buffer)
                if not message:
                    logger.debug(
                        "🔍 [MSG_HANDLER] Failed to decode message from buffer"
                    )
                    # Prevent memory leaks with oversized buffers
                    if len(self.message_buffer) > MAX_BUFFER_SIZE:
                        logger.error("Message buffer too large, clearing buffer")
                        self.message_buffer = b""
                    break

                message_type = message.header.message_type
                request_id = message.get_request_id()
                logger.info(
                    f"🔄 [MSG_HANDLER] Successfully decoded ANPX message, type={message_type}, request_id={request_id}"
                )

                # Calculate message length and remove processed message from buffer
                if len(self.message_buffer) >= 20:  # Minimum header size for length
                    try:
                        # Parse header to get message length (20-byte structured data)
                        header = struct.unpack("!4sBBBBIII", self.message_buffer[:20])
                        total_length = header[5]  # total_length field

                        logger.debug(
                            f"🔍 [MSG_HANDLER] Parsed header: magic={header[0]}, version={header[1]}, "
                            f"msg_type={header[2]}, flags={header[3]}, total_length={total_length}"
                        )

                        if len(self.message_buffer) >= total_length:
                            # Complete message available, remove from buffer
                            self.message_buffer = self.message_buffer[total_length:]
                            logger.debug(
                                f"🔍 [MSG_HANDLER] Processed message of length {total_length}, "
                                f"remaining buffer: {len(self.message_buffer)}"
                            )
                        else:
                            # Message incomplete, wait for more data
                            logger.debug(
                                f"🔍 [MSG_HANDLER] Message incomplete: need {total_length} bytes, "
                                f"have {len(self.message_buffer)}"
                            )
                            break
                    except struct.error as e:
                        logger.warning(
                            f"🔍 [MSG_HANDLER] Failed to parse message header: {e}"
                        )
                        logger.debug(
                            f"🔍 [MSG_HANDLER] Problematic header data: {self.message_buffer[:20].hex()}"
                        )
                        # Remove corrupted header and continue
                        self.message_buffer = self.message_buffer[ANPX_HEADER_SIZE:]
                        continue

                message_type = message.header.message_type
                request_id = message.get_request_id()
                logger.info(
                    f"🔄 [MSG_HANDLER] Processing {message_type} request, request_id={request_id}"
                )

                # Note: Chunked messages are now automatically handled by decoder

                # Route message based on type
                if message.header.message_type == MessageType.HTTP_REQUEST:
                    logger.info("🔄 [MSG_HANDLER] Routing to HTTP request handler")
                    await self._handle_http_request(message)
                elif message.header.message_type == MessageType.ERROR:
                    logger.info("🔄 [MSG_HANDLER] Routing to error message handler")
                    await self._handle_error_message(message)
                else:
                    logger.warning(
                        f"🔍 [MSG_HANDLER] Unsupported message type: {message.header.message_type}"
                    )

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            logger.error(f"Message data length: {len(message_data)} bytes")
            logger.error(f"Buffer size: {len(self.message_buffer)} bytes")
            # Clear buffer on error to prevent cascade failures
            self.message_buffer = b""

    async def _handle_http_request(self, request: ANPXMessage) -> None:
        """
        Handle HTTP request message.

        Args:
            request: ANPX message containing HTTP request
        """
        try:
            request_id = request.get_request_id()
            http_meta = request.get_http_meta()
            request.get_http_body()

            logger.info(
                "🔄 [HTTP_REQUEST] Processing HTTP request",
                request_id=request_id,
                method=http_meta.method if http_meta else "unknown",
                path=http_meta.path if http_meta else "unknown",
            )

            # Process request through ASGI adapter
            response = await self.asgi_adapter.process_request(request)

            logger.info(
                "🔄 [HTTP_REQUEST] Received response from ASGI adapter",
                request_id=request_id,
                status_code=response.status_code,
                response_size=len(response.content),
            )

            # Build ANPX response message using correct protocol structure
            response_header = ANPXHeader(
                message_type=MessageType.HTTP_RESPONSE,
                flags=0,
                total_length=0,  # Will be calculated
                header_crc=0,  # Will be calculated
                body_crc=0,  # Will be calculated
            )

            response_message = ANPXMessage(header=response_header)

            # Add TLV fields for response
            response_message.add_tlv_field(
                TLVTag.REQUEST_ID, request_id if request_id is not None else ""
            )

            # Add response metadata as JSON
            resp_meta = {
                "status": response.status_code,
                "reason": response.reason_phrase or "",
                "headers": dict(response.headers) if response.headers else {},
            }
            response_message.add_tlv_field(TLVTag.RESP_META, json.dumps(resp_meta))

            # Add response body if exists
            if response.content:
                response_message.add_tlv_field(TLVTag.HTTP_BODY, response.content)

            # Send response back to gateway
            if self.send_callback:
                try:
                    self.send_callback(response_message)
                    logger.info(
                        "🟢 [HTTP_REQUEST] Response sent successfully",
                        request_id=request_id,
                        status_code=response.status_code,
                        response_bytes=len(response.content) if response.content else 0,
                    )
                except Exception as send_error:
                    logger.error(
                        f"🔴 [HTTP_REQUEST] Failed to send response: {send_error}"
                    )
                    raise

        except Exception as e:
            request_id = request.get_request_id() or "unknown"
            logger.error(
                f"🔴 [HTTP_REQUEST] Error processing HTTP request {request_id}: {e}"
            )

            # Send error response using correct protocol structure
            error_header = ANPXHeader(
                message_type=MessageType.HTTP_RESPONSE,
                flags=0,
                total_length=0,
                header_crc=0,
                body_crc=0,
            )

            error_response = ANPXMessage(header=error_header)
            error_response.add_tlv_field(TLVTag.REQUEST_ID, request_id)

            error_meta = {
                "status": 500,
                "reason": "Internal Server Error",
                "headers": {"content-type": "text/plain"},
            }
            error_response.add_tlv_field(TLVTag.RESP_META, json.dumps(error_meta))
            error_response.add_tlv_field(TLVTag.HTTP_BODY, b"Internal Server Error")

            if self.send_callback:
                try:
                    self.send_callback(error_response)
                    logger.info(
                        f"🟡 [HTTP_REQUEST] Error response sent for {request_id}"
                    )
                except Exception as send_error:
                    logger.error(
                        f"🔴 [HTTP_REQUEST] Failed to send error response: {send_error}"
                    )

    async def _handle_error_message(self, error_msg: ANPXMessage) -> None:
        """
        Handle ERROR message from gateway.

        Args:
            error_msg: ANPXMessage
        """
        request_id = error_msg.get_request_id()
        error_body = error_msg.get_http_body()
        error_text = error_body.decode("utf-8") if error_body else "Unknown error"

        logger.warning(
            "Received error message from gateway",
            request_id=request_id,
            error=error_text,
        )

    def get_stats(self) -> dict[str, Any]:
        """
        Get message handler statistics.

        Returns:
            dict: Statistics about buffer and processing state
        """
        return {
            "buffer_size": len(self.message_buffer),
            "max_buffer_size": MAX_BUFFER_SIZE,
            "has_send_callback": self.send_callback is not None,
            "encoder_chunk_size": self.encoder.chunk_size,
        }


__all__ = ["MessageHandler"]
