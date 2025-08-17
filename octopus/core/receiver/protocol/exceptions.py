"""Protocol-related exceptions."""


class ANPXError(Exception):
    """Base exception for ANPX protocol errors."""

    pass


class ANPXValidationError(ANPXError):
    """Raised when message validation fails."""

    pass


class ANPXDecodingError(ANPXError):
    """Raised when message decoding fails."""

    pass


class ANPXEncodingError(ANPXError):
    """Raised when message encoding fails."""

    pass


class ANPXChunkingError(ANPXError):
    """Raised when chunking/reassembly fails."""

    pass
