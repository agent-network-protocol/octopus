"""CRC-32 calculation utilities for ANPX protocol."""

import zlib


def calculate_crc32(data: bytes) -> int:
    """
    Calculate CRC-32 checksum for given data.

    Args:
        data: Bytes to calculate CRC for

    Returns:
        CRC-32 checksum as unsigned 32-bit integer
    """
    return zlib.crc32(data) & 0xFFFFFFFF


def verify_crc32(data: bytes, expected_crc: int) -> bool:
    """
    Verify CRC-32 checksum of data.

    Args:
        data: Bytes to verify
        expected_crc: Expected CRC-32 value

    Returns:
        True if CRC matches, False otherwise
    """
    return calculate_crc32(data) == expected_crc
