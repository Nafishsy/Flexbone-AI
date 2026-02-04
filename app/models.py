"""Pydantic models for API responses."""

from typing import Optional
from pydantic import BaseModel


class OCRResponse(BaseModel):
    success: bool
    text: str
    confidence: float
    processing_time_ms: int
    cached: Optional[bool] = None
    message: Optional[str] = None
    metadata: Optional[dict] = None


class BatchItemResponse(BaseModel):
    index: int
    filename: Optional[str]
    success: bool
    text: Optional[str] = None
    confidence: Optional[float] = None
    cached: Optional[bool] = None
    message: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None


class BatchResponse(BaseModel):
    success: bool
    total: int
    processed: int
    results: list[BatchItemResponse]
    processing_time_ms: int


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    status_code: int


class HealthResponse(BaseModel):
    status: str
    service: str
