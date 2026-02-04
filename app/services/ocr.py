"""OCR service using Google Cloud Vision API."""

import logging

from google.cloud import vision
from fastapi import HTTPException, status

from app.utils.image import preprocess_text
from app.services.cache import get_cache_key, get_cached, set_cached

logger = logging.getLogger(__name__)


def perform_ocr(content: bytes) -> dict:
    """Perform OCR using Google Cloud Vision API."""
    logger.info("Calling Vision API for OCR")
    client = vision.ImageAnnotatorClient()
    vision_image = vision.Image(content=content)
    response = client.document_text_detection(image=vision_image)

    if response.error.message:
        logger.error(f"Vision API error: {response.error.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vision API error: {response.error.message}"
        )

    if not response.full_text_annotation.text:
        logger.info("No text found in image")
        return {"text": "", "confidence": 0.0}

    extracted_text = response.full_text_annotation.text
    logger.info(f"Extracted {len(extracted_text)} characters")

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


async def process_image(content: bytes, use_cache: bool = True) -> dict:
    """Process image with caching support."""
    cache_key = get_cache_key(content)

    if use_cache:
        cached = get_cached(cache_key)
        if cached:
            return {**cached, "cached": True}

    ocr_result = perform_ocr(content)
    result = {
        "text": preprocess_text(ocr_result["text"]),
        "confidence": round(ocr_result["confidence"], 4)
    }

    if use_cache:
        set_cached(cache_key, result)

    return result
