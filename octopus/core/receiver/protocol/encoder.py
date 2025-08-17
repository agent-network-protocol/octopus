"""ANPX Protocol Message Encoder."""

import uuid

from .exceptions import ANPXEncodingError
from .message import (
    ANPXHeader,
    ANPXMessage,
    HTTPMeta,
    MessageType,
    ResponseMeta,
    TLVTag,
)


class ANPXEncoder:
    """Encoder for ANPX protocol messages."""

    def __init__(self, chunk_size: int = 64 * 1024) -> None:
        """
        Initialize encoder.

        Args:
            chunk_size: Maximum size for message chunks in bytes
        """
        self.chunk_size = chunk_size

    def encode_http_request(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        query: dict[str, str] | None = None,
        body: bytes | None = None,
        request_id: str | None = None,
    ) -> list[ANPXMessage]:
        """
        Encode HTTP request to ANPX message(s).

        Args:
            method: HTTP method
            path: Request path
            headers: HTTP headers
            query: Query parameters
            body: Request body
            request_id: Unique request ID (generated if None)

        Returns:
            List of ANPX messages (single message or chunks)
        """
        try:
            if request_id is None:
                request_id = str(uuid.uuid4())

            headers = headers or {}
            query = query or {}
            body = body or b""

            # Create HTTP metadata
            http_meta = HTTPMeta(method=method, path=path, headers=headers, query=query)

            # Check if chunking is needed
            meta_json = http_meta.to_json()
            meta_size = len(meta_json.encode("utf-8"))

            # Calculate sizes: RequestID + HTTPMeta + HTTPBody TLV overhead
            base_size = (
                5
                + len(request_id.encode("utf-8"))  # REQUEST_ID TLV
                + 5
                + meta_size  # HTTP_META TLV
                + 5  # HTTP_BODY TLV header
            )

            if len(body) == 0 or base_size + len(body) <= self.chunk_size:
                # Single message
                return [
                    self._create_single_request_message(request_id, http_meta, body)
                ]
            else:
                # Chunked messages
                return self._create_chunked_request_messages(
                    request_id, http_meta, body
                )

        except Exception as e:
            raise ANPXEncodingError(f"Failed to encode HTTP request: {e}") from e

    def encode_http_response(
        self,
        status: int,
        reason: str = "",
        headers: dict[str, str] | None = None,
        body: bytes | None = None,
        request_id: str = "",
    ) -> list[ANPXMessage]:
        """
        Encode HTTP response to ANPX message(s).

        Args:
            status: HTTP status code
            reason: Status reason phrase
            headers: Response headers
            body: Response body
            request_id: Request ID to match with request

        Returns:
            List of ANPX messages (single message or chunks)
        """
        try:
            headers = headers or {}
            body = body or b""

            # Create response metadata
            resp_meta = ResponseMeta(status=status, reason=reason, headers=headers)

            # Check if chunking is needed
            meta_json = resp_meta.to_json()
            meta_size = len(meta_json.encode("utf-8"))

            # Calculate sizes: RequestID + RespMeta + HTTPBody TLV overhead
            base_size = (
                5
                + len(request_id.encode("utf-8"))  # REQUEST_ID TLV
                + 5
                + meta_size  # RESP_META TLV
                + 5  # HTTP_BODY TLV header
            )

            if len(body) == 0 or base_size + len(body) <= self.chunk_size:
                # Single message
                return [
                    self._create_single_response_message(request_id, resp_meta, body)
                ]
            else:
                # Chunked messages
                return self._create_chunked_response_messages(
                    request_id, resp_meta, body
                )

        except Exception as e:
            raise ANPXEncodingError(f"Failed to encode HTTP response: {e}") from e

    def encode_error(
        self, error_message: str, request_id: str | None = None
    ) -> ANPXMessage:
        """
        Encode error message.

        Args:
            error_message: Error description
            request_id: Associated request ID

        Returns:
            ANPX error message
        """
        try:
            header = ANPXHeader(message_type=MessageType.ERROR)
            message = ANPXMessage(header=header)

            if request_id:
                message.add_tlv_field(TLVTag.REQUEST_ID, request_id)

            # Use HTTP_BODY field for error message
            message.add_tlv_field(TLVTag.HTTP_BODY, error_message.encode("utf-8"))

            return message

        except Exception as e:
            raise ANPXEncodingError(f"Failed to encode error message: {e}") from e

    def _create_single_request_message(
        self, request_id: str, http_meta: HTTPMeta, body: bytes
    ) -> ANPXMessage:
        """Create a single HTTP request message."""
        header = ANPXHeader(message_type=MessageType.HTTP_REQUEST)
        message = ANPXMessage(header=header)

        message.add_tlv_field(TLVTag.REQUEST_ID, request_id)
        message.add_tlv_field(TLVTag.HTTP_META, http_meta.to_json())
        if body:
            message.add_tlv_field(TLVTag.HTTP_BODY, body)

        return message

    def _create_single_response_message(
        self, request_id: str, resp_meta: ResponseMeta, body: bytes
    ) -> ANPXMessage:
        """Create a single HTTP response message."""
        header = ANPXHeader(message_type=MessageType.HTTP_RESPONSE)
        message = ANPXMessage(header=header)

        message.add_tlv_field(TLVTag.REQUEST_ID, request_id)
        message.add_tlv_field(TLVTag.RESP_META, resp_meta.to_json())
        if body:
            message.add_tlv_field(TLVTag.HTTP_BODY, body)

        return message

    def _create_chunked_request_messages(
        self, request_id: str, http_meta: HTTPMeta, body: bytes
    ) -> list[ANPXMessage]:
        """Create chunked HTTP request messages."""
        messages = []

        # Calculate chunk size for body (reserve space for metadata in first chunk)
        meta_json = http_meta.to_json()
        first_chunk_overhead = (
            5
            + len(request_id.encode("utf-8"))  # REQUEST_ID TLV
            + 5
            + len(meta_json.encode("utf-8"))  # HTTP_META TLV
            + 5
            + 5
            + 5
            + 5  # CHUNK_IDX + CHUNK_TOT + FINAL_CHUNK + HTTP_BODY TLVs
        )

        first_chunk_body_size = max(0, self.chunk_size - first_chunk_overhead)
        remaining_chunk_size = self.chunk_size - (
            5 + len(request_id.encode("utf-8")) + 5 + 5 + 5 + 5
        )  # Overhead for subsequent chunks

        # Calculate total chunks needed
        if len(body) <= first_chunk_body_size:
            total_chunks = 1
        else:
            remaining_body = len(body) - first_chunk_body_size
            additional_chunks = (
                remaining_body + remaining_chunk_size - 1
            ) // remaining_chunk_size
            total_chunks = 1 + additional_chunks

        # Create chunks
        body_offset = 0

        for chunk_idx in range(total_chunks):
            header = ANPXHeader(message_type=MessageType.HTTP_REQUEST)
            header.set_chunked(True)
            message = ANPXMessage(header=header)

            message.add_tlv_field(TLVTag.REQUEST_ID, request_id)
            message.add_tlv_field(TLVTag.CHUNK_IDX, chunk_idx)
            message.add_tlv_field(TLVTag.CHUNK_TOT, total_chunks)

            # Add metadata only to first chunk
            if chunk_idx == 0:
                message.add_tlv_field(TLVTag.HTTP_META, http_meta.to_json())
                chunk_body_size = min(first_chunk_body_size, len(body) - body_offset)
            else:
                chunk_body_size = min(remaining_chunk_size, len(body) - body_offset)

            # Add body chunk
            if chunk_body_size > 0:
                body_chunk = body[body_offset : body_offset + chunk_body_size]
                message.add_tlv_field(TLVTag.HTTP_BODY, body_chunk)
                body_offset += chunk_body_size

            # Mark final chunk
            if chunk_idx == total_chunks - 1:
                message.add_tlv_field(TLVTag.FINAL_CHUNK, b"\x01")

            messages.append(message)

        return messages

    def _create_chunked_response_messages(
        self, request_id: str, resp_meta: ResponseMeta, body: bytes
    ) -> list[ANPXMessage]:
        """Create chunked HTTP response messages."""
        messages = []

        # Calculate chunk size for body (reserve space for metadata in last chunk)
        meta_json = resp_meta.to_json()
        last_chunk_overhead = (
            5
            + len(request_id.encode("utf-8"))  # REQUEST_ID TLV
            + 5
            + len(meta_json.encode("utf-8"))  # RESP_META TLV
            + 5
            + 5
            + 5
            + 5  # CHUNK_IDX + CHUNK_TOT + FINAL_CHUNK + HTTP_BODY TLVs
        )

        regular_chunk_size = self.chunk_size - (
            5 + len(request_id.encode("utf-8")) + 5 + 5 + 5
        )  # Overhead for regular chunks
        last_chunk_body_size = max(0, self.chunk_size - last_chunk_overhead)

        # Calculate total chunks needed
        if len(body) <= last_chunk_body_size:
            total_chunks = 1
        else:
            body_for_regular_chunks = len(body) - last_chunk_body_size
            regular_chunks = (
                body_for_regular_chunks + regular_chunk_size - 1
            ) // regular_chunk_size
            total_chunks = regular_chunks + 1

        # Create chunks
        body_offset = 0

        for chunk_idx in range(total_chunks):
            header = ANPXHeader(message_type=MessageType.HTTP_RESPONSE)
            header.set_chunked(True)
            message = ANPXMessage(header=header)

            message.add_tlv_field(TLVTag.REQUEST_ID, request_id)
            message.add_tlv_field(TLVTag.CHUNK_IDX, chunk_idx)
            message.add_tlv_field(TLVTag.CHUNK_TOT, total_chunks)

            # Determine chunk body size
            if chunk_idx == total_chunks - 1:
                # Last chunk - add metadata and remaining body
                chunk_body_size = len(body) - body_offset
                message.add_tlv_field(TLVTag.RESP_META, resp_meta.to_json())
                message.add_tlv_field(TLVTag.FINAL_CHUNK, b"\x01")
            else:
                # Regular chunk
                chunk_body_size = min(regular_chunk_size, len(body) - body_offset)

            # Add body chunk
            if chunk_body_size > 0:
                body_chunk = body[body_offset : body_offset + chunk_body_size]
                message.add_tlv_field(TLVTag.HTTP_BODY, body_chunk)
                body_offset += chunk_body_size

            messages.append(message)

        return messages
