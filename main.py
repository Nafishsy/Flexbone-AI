import time
import hashlib
import re
from io import BytesIO
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from google.cloud import vision
from PIL import Image
from PIL.ExifTags import TAGS
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="OCR Image Text Extraction API")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

MAX_FILE_SIZE = 10 * 1024 * 1024
SUPPORTED_FORMATS = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/gif": [".gif"]
}

# Simple in-memory cache
image_cache: dict[str, dict] = {}
MAX_CACHE_SIZE = 100


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": "Rate limit exceeded. Maximum 30 requests per minute.",
            "status_code": 429
        }
    )


def is_valid_image(content_type: str, filename: str) -> bool:
    filename_lower = filename.lower() if filename else ""
    for mime, extensions in SUPPORTED_FORMATS.items():
        if content_type == mime:
            return True
        if any(filename_lower.endswith(ext) for ext in extensions):
            return True
    return False


def get_supported_formats() -> str:
    return "JPG, PNG, GIF"


def preprocess_text(text: str) -> str:
    if not text:
        return ""
    # Normalize whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    # Normalize line breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip leading/trailing whitespace from lines
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    return text.strip()


def get_cache_key(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def extract_metadata(content: bytes) -> Optional[dict]:
    try:
        img = Image.open(BytesIO(content))
        metadata = {
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height
        }
        # Extract EXIF data if available
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
    except Exception:
        return None


def perform_ocr(content: bytes) -> dict:
    client = vision.ImageAnnotatorClient()
    vision_image = vision.Image(content=content)
    response = client.document_text_detection(image=vision_image)

    if response.error.message:
        raise HTTPException(
            status_code=500,
            detail=f"Vision API error: {response.error.message}"
        )

    if not response.full_text_annotation.text:
        return {"text": "", "confidence": 0.0}

    extracted_text = response.full_text_annotation.text

    confidence = 0.0
    if response.full_text_annotation.pages:
        confidences = []
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                if block.confidence > 0:
                    confidences.append(block.confidence)
        if confidences:
            confidence = sum(confidences) / len(confidences)

    return {"text": extracted_text, "confidence": confidence}


async def process_single_image(content: bytes, use_cache: bool = True) -> dict:
    cache_key = get_cache_key(content)

    if use_cache and cache_key in image_cache:
        cached = image_cache[cache_key]
        return {**cached, "cached": True}

    ocr_result = perform_ocr(content)
    result = {
        "text": preprocess_text(ocr_result["text"]),
        "confidence": round(ocr_result["confidence"], 4)
    }

    if use_cache:
        if len(image_cache) >= MAX_CACHE_SIZE:
            oldest_key = next(iter(image_cache))
            del image_cache[oldest_key]
        image_cache[cache_key] = result

    return result


@app.get("/")
def health_check():
    return {"status": "healthy", "service": "OCR API"}


@app.post("/extract-text")
@limiter.limit("30/minute")
async def extract_text(
    request: Request,
    image: UploadFile = File(...),
    include_metadata: bool = False
):
    start_time = time.time()

    if not is_valid_image(image.content_type, image.filename or ""):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Supported formats: {get_supported_formats()}"
        )

    content = await image.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB."
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    try:
        result = await process_single_image(content)
        processing_time_ms = int((time.time() - start_time) * 1000)

        response_data = {
            "success": True,
            "text": result["text"],
            "confidence": result["confidence"],
            "processing_time_ms": processing_time_ms
        }

        if result.get("cached"):
            response_data["cached"] = True

        if not result["text"]:
            response_data["message"] = "No text found in image"

        if include_metadata:
            metadata = extract_metadata(content)
            if metadata:
                response_data["metadata"] = metadata

        return JSONResponse(content=response_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")


@app.post("/extract-text/batch")
@limiter.limit("10/minute")
async def extract_text_batch(
    request: Request,
    images: list[UploadFile] = File(...),
    include_metadata: bool = False
):
    start_time = time.time()

    if len(images) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 images per batch request."
        )

    results = []
    for idx, image in enumerate(images):
        item_result = {"index": idx, "filename": image.filename}

        if not is_valid_image(image.content_type, image.filename or ""):
            item_result["success"] = False
            item_result["error"] = f"Invalid file type. Supported formats: {get_supported_formats()}"
            results.append(item_result)
            continue

        content = await image.read()
        if len(content) > MAX_FILE_SIZE:
            item_result["success"] = False
            item_result["error"] = "File too large. Maximum size is 10MB."
            results.append(item_result)
            continue

        if len(content) == 0:
            item_result["success"] = False
            item_result["error"] = "Empty file."
            results.append(item_result)
            continue

        try:
            ocr_result = await process_single_image(content)
            item_result["success"] = True
            item_result["text"] = ocr_result["text"]
            item_result["confidence"] = ocr_result["confidence"]
            if ocr_result.get("cached"):
                item_result["cached"] = True
            if not ocr_result["text"]:
                item_result["message"] = "No text found in image"
            if include_metadata:
                metadata = extract_metadata(content)
                if metadata:
                    item_result["metadata"] = metadata
        except Exception as e:
            item_result["success"] = False
            item_result["error"] = str(e)

        results.append(item_result)

    processing_time_ms = int((time.time() - start_time) * 1000)

    return JSONResponse(content={
        "success": True,
        "total": len(images),
        "processed": len([r for r in results if r.get("success")]),
        "results": results,
        "processing_time_ms": processing_time_ms
    })


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
