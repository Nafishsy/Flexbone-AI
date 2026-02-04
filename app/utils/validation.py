"""File validation utilities."""

from io import BytesIO
from PIL import Image

from app.config import SUPPORTED_FORMATS, IMAGE_SIGNATURES, MAX_FILE_SIZE


def is_valid_content_type(content_type: str, filename: str) -> bool:
    """Validate file by content type or extension."""
    filename_lower = filename.lower() if filename else ""
    for mime, extensions in SUPPORTED_FORMATS.items():
        if content_type == mime:
            return True
        if any(filename_lower.endswith(ext) for ext in extensions):
            return True
    return False


def validate_image_signature(content: bytes) -> bool:
    """Validate image by checking magic bytes."""
    for signature in IMAGE_SIGNATURES:
        if content.startswith(signature):
            return True
    return False


def validate_image_integrity(content: bytes) -> bool:
    """Verify image can be opened and is not corrupted."""
    try:
        img = Image.open(BytesIO(content))
        img.verify()
        return True
    except Exception:
        return False


def validate_file_size(content: bytes) -> bool:
    """Check if file size is within limits."""
    return len(content) <= MAX_FILE_SIZE


def get_supported_formats() -> str:
    """Return human-readable supported formats string."""
    return "JPG, PNG, GIF"
