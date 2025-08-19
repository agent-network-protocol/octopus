"""Chunk assembly and management for ANPX protocol."""

import time

from .exceptions import ANPXChunkingError
from .message import ANPXHeader, ANPXMessage, MessageType, TLVTag


class ChunkAssembler:
    """Assembles chunked ANPX messages."""

    def __init__(self) -> None:
        """Initialize chunk assembler."""
        self.chunks: dict[str, list[ANPXMessage]] = {}
        self.timestamps: dict[str, float] = {}

    def add_chunk(self, request_id: str, chunk: ANPXMessage) -> ANPXMessage | None:
        """
        Add a chunk and attempt to assemble complete message.

        Args:
            request_id: Request ID for chunk grouping
            chunk: Individual chunk message

        Returns:
            Complete assembled message if all chunks received, None otherwise

        Raises:
            ANPXChunkingError: If chunk assembly fails
        """
        try:
            # Initialize chunk list for this request_id if needed
            if request_id not in self.chunks:
                self.chunks[request_id] = []
                self.timestamps[request_id] = time.time()

            # Validate chunk
            chunk_idx, chunk_tot, is_final = chunk.get_chunk_info()

            if chunk_idx is None:
                raise ANPXChunkingError("Chunk missing chunk_idx")

            # Check for duplicate chunks
            existing_indices = {c.get_chunk_info()[0] for c in self.chunks[request_id]}
            if chunk_idx in existing_indices:
                raise ANPXChunkingError(f"Duplicate chunk index {chunk_idx}")

            # Add chunk to list
            self.chunks[request_id].append(chunk)

            # Check if assembly is complete
            if is_final or (
                chunk_tot is not None and len(self.chunks[request_id]) == chunk_tot
            ):
                return self._assemble_chunks(request_id)

            return None

        except Exception as e:
            raise ANPXChunkingError(f"Failed to add chunk: {e}") from e

    def _assemble_chunks(self, request_id: str) -> ANPXMessage:
        """
        Assemble chunks into complete message.

        Args:
            request_id: Request ID to assemble

        Returns:
            Complete assembled message

        Raises:
            ANPXChunkingError: If assembly fails
        """
        try:
            chunks = self.chunks[request_id]

            if not chunks:
                raise ANPXChunkingError("No chunks to assemble")

            # Sort chunks by index
            chunks.sort(key=lambda c: c.get_chunk_info()[0] or 0)

            # Validate chunk sequence
            expected_indices = list(range(len(chunks)))
            actual_indices = [c.get_chunk_info()[0] for c in chunks]

            if actual_indices != expected_indices:
                raise ANPXChunkingError(
                    f"Missing or invalid chunk indices. Expected {expected_indices}, got {actual_indices}"
                )

            # Determine message type from first chunk
            first_chunk = chunks[0]
            message_type = first_chunk.header.message_type

            # Assemble based on message type
            if message_type == MessageType.HTTP_REQUEST:
                return self._assemble_request_chunks(chunks)
            elif message_type == MessageType.HTTP_RESPONSE:
                return self._assemble_response_chunks(chunks)
            else:
                raise ANPXChunkingError(
                    f"Cannot assemble chunks for message type {message_type}"
                )

        finally:
            # Clean up chunks after assembly
            self._cleanup_request(request_id)

    def _assemble_request_chunks(self, chunks: list[ANPXMessage]) -> ANPXMessage:
        """Assemble HTTP request chunks."""
        first_chunk = chunks[0]

        # Create new header (non-chunked)
        header = ANPXHeader(message_type=MessageType.HTTP_REQUEST)
        assembled = ANPXMessage(header=header)

        # Get request ID and metadata from first chunk
        request_id = first_chunk.get_request_id()
        http_meta = first_chunk.get_http_meta()

        if not request_id:
            raise ANPXChunkingError("First chunk missing request_id")
        if not http_meta:
            raise ANPXChunkingError("First chunk missing http_meta")

        # Add request ID and metadata
        assembled.add_tlv_field(TLVTag.REQUEST_ID, request_id)
        assembled.add_tlv_field(TLVTag.HTTP_META, http_meta.to_json())

        # Assemble body from all chunks
        body_parts = []
        for chunk in chunks:
            body_part = chunk.get_http_body()
            if body_part:
                body_parts.append(body_part)

        if body_parts:
            complete_body = b"".join(body_parts)
            assembled.add_tlv_field(TLVTag.HTTP_BODY, complete_body)

        return assembled

    def _assemble_response_chunks(self, chunks: list[ANPXMessage]) -> ANPXMessage:
        """Assemble HTTP response chunks."""
        # Find the chunk with response metadata (usually the last one)
        resp_meta = None
        request_id = None

        for chunk in chunks:
            if chunk.get_resp_meta():
                resp_meta = chunk.get_resp_meta()
            if chunk.get_request_id():
                request_id = chunk.get_request_id()

        if not request_id:
            raise ANPXChunkingError("No chunk contains request_id")
        if not resp_meta:
            raise ANPXChunkingError("No chunk contains response metadata")

        # Create new header (non-chunked)
        header = ANPXHeader(message_type=MessageType.HTTP_RESPONSE)
        assembled = ANPXMessage(header=header)

        # Add request ID and metadata
        assembled.add_tlv_field(TLVTag.REQUEST_ID, request_id)
        assembled.add_tlv_field(TLVTag.RESP_META, resp_meta.to_json())

        # Assemble body from all chunks
        body_parts = []
        for chunk in chunks:
            body_part = chunk.get_http_body()
            if body_part:
                body_parts.append(body_part)

        if body_parts:
            complete_body = b"".join(body_parts)
            assembled.add_tlv_field(TLVTag.HTTP_BODY, complete_body)

        return assembled

    def _cleanup_request(self, request_id: str) -> None:
        """Clean up chunks for a request."""
        self.chunks.pop(request_id, None)
        self.timestamps.pop(request_id, None)

    def cleanup_stale(self, max_age_seconds: float) -> int:
        """
        Clean up stale chunk assemblies.

        Args:
            max_age_seconds: Maximum age for assemblies

        Returns:
            Number of assemblies cleaned up
        """
        current_time = time.time()
        stale_requests = [
            req_id
            for req_id, timestamp in self.timestamps.items()
            if current_time - timestamp > max_age_seconds
        ]

        for req_id in stale_requests:
            self._cleanup_request(req_id)

        return len(stale_requests)
