"""Application configuration constants."""

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

SUPPORTED_FORMATS = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/gif": [".gif"]
}

IMAGE_SIGNATURES = {
    b'\xff\xd8\xff': 'jpeg',
    b'\x89PNG\r\n\x1a\n': 'png',
    b'GIF87a': 'gif',
    b'GIF89a': 'gif'
}

MAX_CACHE_SIZE = 100
MAX_BATCH_SIZE = 10

RATE_LIMIT_SINGLE = "30/minute"
RATE_LIMIT_BATCH = "10/minute"
