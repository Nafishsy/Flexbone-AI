"""OCR API endpoints."""

import time
import logging

from fastapi import APIRouter, File, UploadFile, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.dependencies import limiter
from app.config import MAX_FILE_SIZE, MAX_BATCH_SIZE
from app.services.ocr import process_image
from app.utils.validation import (
    is_valid_content_type,
    validate_image_signature,
    validate_image_integrity,
    get_supported_formats
)
from app.utils.image import extract_metadata

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/extract-text", summary="Extract text from image",
    responses={
        200: {"description": "Text extracted successfully"},
        400: {"description": "Empty or corrupted file"},
        413: {"description": "File too large (max 10MB)"},
        415: {"description": "Unsupported file type"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "OCR processing failed"}
    })
@limiter.limit("30/minute")
async def extract_text(
    request: Request,
    image: UploadFile = File(..., description="Image file (JPG, PNG, or GIF, max 10MB)"),
    include_metadata: bool = False
):
    """
    Extract text from a single uploaded image using OCR.

    - **image**: Image file to process (JPG, PNG, GIF)
    - **include_metadata**: Set to true to include image dimensions and EXIF data

    Returns extracted text with confidence score and processing time.
    """
    start_time = time.time()
    logger.info(f"Processing image: {image.filename}")

    if not is_valid_content_type(image.content_type, image.filename or ""):
        logger.warning(f"Invalid file type: {image.content_type}")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Supported formats: {get_supported_formats()}"
        )

    content = await image.read()

    if len(content) > MAX_FILE_SIZE:
        logger.warning(f"File too large: {len(content)} bytes")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 10MB."
        )

    if len(content) == 0:
        logger.warning("Empty file uploaded")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded."
        )

    if not validate_image_signature(content):
        logger.warning("Invalid image signature (magic bytes)")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid image file. File content does not match image format."
        )

    if not validate_image_integrity(content):
        logger.warning("Corrupted image file")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Corrupted or invalid image file."
        )

    try:
        result = await process_image(content)
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

        logger.info(f"Request completed in {processing_time_ms}ms")
        return JSONResponse(content=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}"
        )


@router.post("/extract-text/batch", summary="Batch extract text from multiple images",
    responses={
        200: {"description": "Batch processed successfully"},
        400: {"description": "Batch size exceeded or invalid files"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Processing failed"}
    })
@limiter.limit("10/minute")
async def extract_text_batch(
    request: Request,
    images: list[UploadFile] = File(..., description="Multiple image files (max 10)"),
    include_metadata: bool = False
):
    """
    Process multiple images in a single request.

    - **images**: Up to 10 image files (JPG, PNG, GIF)
    - **include_metadata**: Include image metadata for each result

    Returns individual results for each image with success/failure status.
    """
    start_time = time.time()
    logger.info(f"Batch processing {len(images)} images")

    if len(images) > MAX_BATCH_SIZE:
        logger.warning(f"Batch size exceeded: {len(images)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_BATCH_SIZE} images per batch request."
        )

    results = []
    for idx, image in enumerate(images):
        item_result = {"index": idx, "filename": image.filename}
        logger.info(f"Processing batch item {idx}: {image.filename}")

        if not is_valid_content_type(image.content_type, image.filename or ""):
            item_result["success"] = False
            item_result["error"] = f"Unsupported file type. Supported formats: {get_supported_formats()}"
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

        if not validate_image_signature(content):
            item_result["success"] = False
            item_result["error"] = "Invalid image file. File content does not match image format."
            results.append(item_result)
            continue

        if not validate_image_integrity(content):
            item_result["success"] = False
            item_result["error"] = "Corrupted or invalid image file."
            results.append(item_result)
            continue

        try:
            ocr_result = await process_image(content)
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
            logger.error(f"Batch item {idx} failed: {e}")
            item_result["success"] = False
            item_result["error"] = str(e)

        results.append(item_result)

    processing_time_ms = int((time.time() - start_time) * 1000)
    processed_count = len([r for r in results if r.get("success")])
    logger.info(f"Batch completed: {processed_count}/{len(images)} in {processing_time_ms}ms")

    return JSONResponse(content={
        "success": True,
        "total": len(images),
        "processed": processed_count,
        "results": results,
        "processing_time_ms": processing_time_ms
    })
