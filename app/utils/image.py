"""Image processing utilities."""

import re
import logging
from io import BytesIO
from typing import Optional

from PIL import Image
from PIL.ExifTags import TAGS

logger = logging.getLogger(__name__)


def preprocess_text(text: str) -> str:
    """Clean and normalize extracted text."""
    if not text:
        return ""
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    return text.strip()


def extract_metadata(content: bytes) -> Optional[dict]:
    """Extract image metadata including EXIF data."""
    try:
        img = Image.open(BytesIO(content))
        metadata = {
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height
        }
        exif_data = img._getexif()
        if exif_data:
            exif = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                if isinstance(value, bytes):
                    continue
                if tag in ["Make", "Model", "DateTime", "Software", "Orientation"]:
                    exif[tag] = str(value)
            if exif:
                metadata["exif"] = exif
        return metadata
    except Exception as e:
        logger.debug(f"Failed to extract metadata: {e}")
        return None
