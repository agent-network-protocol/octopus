"""ANPX Protocol Message Decoder."""

from .chunking import ChunkAssembler
from .crc import verify_crc32
from .exceptions import ANPXDecodingError, ANPXValidationError
from .message import ANPXHeader, ANPXMessage, TLVField


class ANPXDecoder:
    """Decoder for ANPX protocol messages."""

    def __init__(self) -> None:
        """Initialize decoder with chunk assembler."""
        self.chunk_assembler = ChunkAssembler()

    def decode_message(self, data: bytes) -> ANPXMessage | None:
        """
        Decode ANPX message from bytes.

        Args:
            data: Raw message bytes

        Returns:
            Decoded message, or None if chunked and not complete yet

        Raises:
            ANPXDecodingError: If decoding fails
            ANPXValidationError: If validation fails
        """
        try:
            if len(data) < ANPXHeader.HEADER_SIZE:
                raise ANPXDecodingError(f"Data too short for header: {len(data)} bytes")

            # Decode header
            header = ANPXHeader.decode(data[: ANPXHeader.HEADER_SIZE])

            # Validate total length
            if len(data) != header.total_length:
                raise ANPXValidationError(
                    f"Data length {len(data)} != header total_length {header.total_length}"
                )

            # Extract and validate body
            body_data = data[ANPXHeader.HEADER_SIZE :]
            if not verify_crc32(body_data, header.body_crc):
                raise ANPXValidationError("Body CRC validation failed")

            # Decode TLV fields
            tlv_fields = self._decode_tlv_fields(body_data)

            # Create message
            message = ANPXMessage(header=header, tlv_fields=tlv_fields)

            # Handle chunked messages
            if header.is_chunked:
                return self._handle_chunked_message(message)
            else:
                return message

        except (ANPXDecodingError, ANPXValidationError):
            raise
        except Exception as e:
            raise ANPXDecodingError(f"Failed to decode message: {e}") from e

    def _decode_tlv_fields(self, body_data: bytes) -> list[TLVField]:
        """Decode all TLV fields from body data."""
        fields = []
        offset = 0

        while offset < len(body_data):
            try:
                field, offset = TLVField.decode(body_data, offset)
                fields.append(field)
            except ValueError as e:
                # Skip unknown tags gracefully
                if "Unknown tag" in str(e):
                    # Try to skip this field by reading tag and length
                    if offset + 5 <= len(body_data):
                        import struct

                        _, length = struct.unpack("!BI", body_data[offset : offset + 5])
                        offset += 5 + length
                        continue
                raise ANPXDecodingError(f"Failed to decode TLV field: {e}") from e

        return fields

    def _handle_chunked_message(self, chunk: ANPXMessage) -> ANPXMessage | None:
        """
        Handle a chunked message.

        Args:
            chunk: Individual chunk message

        Returns:
            Complete message if all chunks received, None otherwise
        """
        request_id = chunk.get_request_id()
        if not request_id:
            raise ANPXValidationError("Chunked message missing request_id")

        # Add chunk to assembler
        complete_message = self.chunk_assembler.add_chunk(request_id, chunk)

        return complete_message

    def get_pending_chunks(self) -> dict[str, int]:
        """
        Get information about pending chunk assemblies.

        Returns:
            Dict mapping request_id to number of chunks received
        """
        return {
            req_id: len(chunks)
            for req_id, chunks in self.chunk_assembler.chunks.items()
        }

    def cleanup_stale_chunks(self, max_age_seconds: float = 300.0) -> int:
        """
        Clean up stale chunk assemblies.

        Args:
            max_age_seconds: Maximum age for chunk assemblies

        Returns:
            Number of assemblies cleaned up
        """
        return self.chunk_assembler.cleanup_stale(max_age_seconds)
