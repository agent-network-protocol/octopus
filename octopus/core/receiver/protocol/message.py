"""ANPX Protocol Message Structures."""

import json
import struct
import zlib
from dataclasses import dataclass, field
from enum import IntEnum

try:
    from octopus.utils.log_base import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger(__name__)


class MessageType(IntEnum):
    """ANPX Message Types."""

    HTTP_REQUEST = 0x01
    HTTP_RESPONSE = 0x02
    ERROR = 0xFF


class TLVTag(IntEnum):
    """TLV Tag definitions."""

    REQUEST_ID = 0x01
    HTTP_META = 0x02
    HTTP_BODY = 0x03
    RESP_META = 0x04
    CHUNK_IDX = 0x0A
    CHUNK_TOT = 0x0B
    FINAL_CHUNK = 0x0C


@dataclass
class TLVField:
    """Represents a single TLV field."""

    tag: TLVTag
    value: bytes

    @property
    def length(self) -> int:
        """Get the length of value."""
        return len(self.value)

    def encode(self) -> bytes:
        """Encode TLV field to bytes."""
        return struct.pack("!BI", self.tag, self.length) + self.value

    @classmethod
    def decode(cls, data: bytes, offset: int = 0) -> tuple["TLVField", int]:
        """
        Decode TLV field from bytes.

        Returns:
            Tuple of (TLVField, next_offset)
        """
        if len(data) < offset + 5:  # Tag(1) + Length(4)
            raise ValueError("Insufficient data for TLV header")

        tag, length = struct.unpack("!BI", data[offset : offset + 5])

        if len(data) < offset + 5 + length:
            raise ValueError("Insufficient data for TLV value")

        value = data[offset + 5 : offset + 5 + length]

        return cls(TLVTag(tag), value), offset + 5 + length


@dataclass
class ANPXHeader:
    """ANPX Protocol Fixed Header (24 bytes)."""

    MAGIC = b"ANPX"
    VERSION = 0x01
    HEADER_SIZE = 24

    message_type: MessageType
    flags: int = 0
    total_length: int = 0
    header_crc: int = 0
    body_crc: int = 0

    @property
    def is_chunked(self) -> bool:
        """Check if this is a chunked message."""
        return bool(self.flags & 0x01)

    def set_chunked(self, chunked: bool = True) -> None:
        """Set or clear the chunked flag."""
        if chunked:
            self.flags |= 0x01
        else:
            self.flags &= ~0x01

    def encode(self) -> bytes:
        """Encode header to 24 bytes."""
        logger.debug(
            f"🔧 [HEADER_ENCODE] Starting header encode",
            message_type=self.message_type,
            flags=self.flags,
            total_length=self.total_length,
            body_crc=f"{self.body_crc:08x}",
        )

        # Encode header without CRC first
        header_data = struct.pack(
            "!4sBBBBIII",
            self.MAGIC,
            self.VERSION,
            self.message_type,
            self.flags,
            0,  # Reserved
            self.total_length,
            0,  # Placeholder for header_crc
            self.body_crc,
        )

        # Calculate and insert header CRC (first 12 bytes)
        from .crc import calculate_crc32

        crc_data = header_data[:12]
        header_crc = calculate_crc32(crc_data)

        logger.debug(
            f"🔧 [HEADER_ENCODE] CRC calculation",
            crc_data=crc_data.hex(),
            calculated_crc=f"{header_crc:08x}",
        )

        # Encode final header with calculated CRC
        final_header = struct.pack(
            "!4sBBBBIII",
            self.MAGIC,
            self.VERSION,
            self.message_type,
            self.flags,
            0,  # Reserved
            self.total_length,
            header_crc,
            self.body_crc,
        )

        # Ensure header is exactly 24 bytes by adding padding if needed
        if len(final_header) < self.HEADER_SIZE:
            final_header += b"\x00" * (self.HEADER_SIZE - len(final_header))

        result = final_header[: self.HEADER_SIZE]
        logger.debug(
            f"🔧 [HEADER_ENCODE] Header encode completed",
            final_header=result.hex(),
            header_size=len(result),
        )

        return result

    @classmethod
    def decode(cls, data: bytes) -> "ANPXHeader":
        """Decode header from 24 bytes."""
        logger.debug(
            f"🔍 [HEADER_DECODE] Starting header decode", data_length=len(data)
        )
        logger.debug(f"🔍 [HEADER_DECODE] Raw header data", raw_data=data[:24].hex())

        if len(data) < cls.HEADER_SIZE:
            logger.error(
                f"🔍 [HEADER_DECODE] Header too short",
                expected=cls.HEADER_SIZE,
                actual=len(data),
            )
            raise ValueError(
                f"Header data must be {cls.HEADER_SIZE} bytes, got {len(data)}"
            )

        # Unpack the 20-byte structured data from 24-byte header (last 4 bytes are padding)
        magic, version, msg_type, flags, reserved, total_len, header_crc, body_crc = (
            struct.unpack("!4sBBBBIII", data[:20])
        )

        logger.debug(
            f"🔍 [HEADER_DECODE] Unpacked header fields",
            magic=magic,
            version=version,
            msg_type=msg_type,
            flags=flags,
            total_len=total_len,
            header_crc=f"{header_crc:08x}",
            body_crc=f"{body_crc:08x}",
        )

        if magic != cls.MAGIC:
            logger.error(
                f"🔍 [HEADER_DECODE] Invalid magic", expected=cls.MAGIC, actual=magic
            )
            raise ValueError(f"Invalid magic: {magic}")

        if version != cls.VERSION:
            logger.error(
                f"🔍 [HEADER_DECODE] Unsupported version",
                expected=cls.VERSION,
                actual=version,
            )
            raise ValueError(f"Unsupported version: {version}")

        # Verify header CRC (first 12 bytes)
        from .crc import verify_crc32

        header_data_for_crc = data[:12]
        calculated_crc = zlib.crc32(header_data_for_crc) & 0xFFFFFFFF

        logger.debug(
            f"🔍 [HEADER_DECODE] CRC verification",
            header_data=header_data_for_crc.hex(),
            expected_crc=f"{header_crc:08x}",
            calculated_crc=f"{calculated_crc:08x}",
        )

        if not verify_crc32(header_data_for_crc, header_crc):
            logger.error(
                f"🔍 [HEADER_DECODE] CRC validation failed",
                expected=f"{header_crc:08x}",
                calculated=f"{calculated_crc:08x}",
                header_data=header_data_for_crc.hex(),
            )
            raise ValueError("Header CRC validation failed")

        logger.debug(f"🔍 [HEADER_DECODE] Header decode completed successfully")

        return cls(
            message_type=MessageType(msg_type),
            flags=flags,
            total_length=total_len,
            header_crc=header_crc,
            body_crc=body_crc,
        )


@dataclass
class HTTPMeta:
    """HTTP request metadata."""

    method: str
    path: str
    headers: dict[str, str] = field(default_factory=dict)
    query: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps({
            "method": self.method,
            "path": self.path,
            "headers": self.headers,
            "query": self.query,
        })

    @classmethod
    def from_json(cls, json_str: str) -> "HTTPMeta":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls(
            method=data["method"],
            path=data["path"],
            headers=data.get("headers", {}),
            query=data.get("query", {}),
        )


@dataclass
class ResponseMeta:
    """HTTP response metadata."""

    status: int
    reason: str = ""
    headers: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps({
            "status": self.status,
            "reason": self.reason,
            "headers": self.headers,
        })

    @classmethod
    def from_json(cls, json_str: str) -> "ResponseMeta":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls(
            status=data["status"],
            reason=data.get("reason", ""),
            headers=data.get("headers", {}),
        )


@dataclass
class ANPXMessage:
    """Complete ANPX Protocol Message."""

    header: ANPXHeader
    tlv_fields: list[TLVField] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Update header total_length after initialization."""
        self._update_total_length()

    def _update_total_length(self) -> None:
        """Update header total_length based on current TLV fields."""
        body_size = sum(
            5 + tlv_field.length for tlv_field in self.tlv_fields
        )  # Tag(1) + Len(4) + Value
        self.header.total_length = ANPXHeader.HEADER_SIZE + body_size

    def add_tlv_field(self, tag: TLVTag, value: str | bytes | int) -> None:
        """Add a TLV field to the message."""
        if isinstance(value, str):
            value_bytes = value.encode("utf-8")
        elif isinstance(value, int):
            value_bytes = struct.pack("!I", value)
        else:
            value_bytes = value

        self.tlv_fields.append(TLVField(tag, value_bytes))
        self._update_total_length()

    def get_tlv_field(self, tag: TLVTag) -> TLVField | None:
        """Get first TLV field with specified tag."""
        for tlv_field in self.tlv_fields:
            if tlv_field.tag == tag:
                return tlv_field
        return None

    def get_tlv_value_str(self, tag: TLVTag) -> str | None:
        """Get TLV field value as string."""
        field = self.get_tlv_field(tag)
        return field.value.decode("utf-8") if field else None

    def get_tlv_value_int(self, tag: TLVTag) -> int | None:
        """Get TLV field value as integer."""
        field = self.get_tlv_field(tag)
        if field and len(field.value) == 4:
            return struct.unpack("!I", field.value)[0]
        return None

    def get_request_id(self) -> str | None:
        """Get request ID from TLV fields."""
        return self.get_tlv_value_str(TLVTag.REQUEST_ID)

    def get_http_meta(self) -> HTTPMeta | None:
        """Get HTTP metadata from TLV fields."""
        json_str = self.get_tlv_value_str(TLVTag.HTTP_META)
        return HTTPMeta.from_json(json_str) if json_str else None

    def get_resp_meta(self) -> ResponseMeta | None:
        """Get response metadata from TLV fields."""
        json_str = self.get_tlv_value_str(TLVTag.RESP_META)
        return ResponseMeta.from_json(json_str) if json_str else None

    def get_http_body(self) -> bytes | None:
        """Get HTTP body from TLV fields."""
        field = self.get_tlv_field(TLVTag.HTTP_BODY)
        return field.value if field else None

    def is_chunked(self) -> bool:
        """Check if this is a chunked message."""
        return self.header.is_chunked

    def get_chunk_info(self) -> tuple[int | None, int | None, bool]:
        """
        Get chunking information.

        Returns:
            Tuple of (chunk_idx, chunk_total, is_final)
        """
        chunk_idx = self.get_tlv_value_int(TLVTag.CHUNK_IDX)
        chunk_tot = self.get_tlv_value_int(TLVTag.CHUNK_TOT)

        final_field = self.get_tlv_field(TLVTag.FINAL_CHUNK)
        is_final = bool(final_field and final_field.value == b"\x01")

        return chunk_idx, chunk_tot, is_final

    def encode_body(self) -> bytes:
        """Encode TLV body to bytes."""
        body = b""
        for tlv_field in self.tlv_fields:
            body += tlv_field.encode()
        return body

    def encode(self) -> bytes:
        """Encode complete message to bytes."""
        # First encode body to calculate CRC
        body = self.encode_body()

        # Update header with body CRC
        from .crc import calculate_crc32

        self.header.body_crc = calculate_crc32(body)
        self._update_total_length()

        # Encode header and combine
        header_bytes = self.header.encode()
        return header_bytes + body
