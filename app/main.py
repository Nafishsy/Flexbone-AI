"""FastAPI application initialization."""

import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.dependencies import limiter
from app.routers import ocr

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app with enhanced documentation
app = FastAPI(
    title="OCR Image Text Extraction API",
    description="""
## Overview
A serverless OCR API that extracts text from images using Google Cloud Vision API.

## Features
- **Multi-format support:** JPG, PNG, GIF
- **Confidence scores:** Block-level confidence from Vision API
- **Text preprocessing:** Whitespace and linebreak normalization
- **Rate limiting:** 30 requests/min (single), 10 requests/min (batch)
- **Caching:** SHA-256 based caching for identical images
- **Batch processing:** Process up to 10 images per request
- **Image metadata:** Optional EXIF and dimension extraction

## Authentication
No authentication required. Public API.

## Rate Limits
| Endpoint | Limit |
|----------|-------|
| `/extract-text` | 30 requests/minute |
| `/extract-text/batch` | 10 requests/minute |
    """,
    version="1.0.0",
    contact={
        "name": "API Support",
    },
    license_info={
        "name": "MIT",
    },
)

# Attach limiter
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Include router with tags
app.include_router(ocr.router, tags=["OCR"])


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded")
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": "Rate limit exceeded.",
            "status_code": 429
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.get("/", tags=["Health"])
def health_check():
    """
    Health check endpoint.

    Returns the service status.
    """
    return {"status": "healthy", "service": "OCR API"}
