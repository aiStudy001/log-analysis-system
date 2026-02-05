"""
Standard Error Response Models

Provides consistent error response structure across all API endpoints.
"""
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """Standard error codes for API responses"""

    # Client errors (4xx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_SQL = "INVALID_SQL"
    MISSING_PARAMETER = "MISSING_PARAMETER"
    INVALID_REQUEST = "INVALID_REQUEST"

    # Server errors (5xx)
    DATABASE_ERROR = "DATABASE_ERROR"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_ERROR = "LLM_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    WEBSOCKET_ERROR = "WEBSOCKET_ERROR"

    # Service errors (503)
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    CONNECTION_POOL_EXHAUSTED = "CONNECTION_POOL_EXHAUSTED"

    # Unknown errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class ErrorResponse(BaseModel):
    """
    Standardized error response model

    Attributes:
        error_code: Machine-readable error code
        message: Human-readable error message
        request_id: Unique request identifier for tracing
        timestamp: When the error occurred
        details: Optional additional error details (sanitized)
        retry_after: Optional seconds until retry allowed
    """

    error_code: ErrorCode = Field(..., description="Error code for categorization")
    message: str = Field(..., description="User-friendly error message")
    request_id: str = Field(..., description="Request ID for debugging")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    retry_after: Optional[int] = Field(None, description="Seconds until retry allowed")

    class Config:
        json_schema_extra = {
            "example": {
                "error_code": "DATABASE_ERROR",
                "message": "Database connection failed",
                "request_id": "req_abc123",
                "timestamp": "2026-02-05T10:30:00",
                "details": {"error_type": "ConnectionError"},
                "retry_after": 5
            }
        }


def get_http_status_for_error_code(error_code: ErrorCode) -> int:
    """
    Map error codes to HTTP status codes

    Args:
        error_code: Error code enum

    Returns:
        HTTP status code (400, 500, 503, 504)
    """
    status_mapping = {
        # 400 Bad Request
        ErrorCode.VALIDATION_ERROR: 400,
        ErrorCode.INVALID_SQL: 400,
        ErrorCode.MISSING_PARAMETER: 400,
        ErrorCode.INVALID_REQUEST: 400,

        # 500 Internal Server Error
        ErrorCode.DATABASE_ERROR: 500,
        ErrorCode.LLM_ERROR: 500,
        ErrorCode.INTERNAL_ERROR: 500,
        ErrorCode.WEBSOCKET_ERROR: 500,
        ErrorCode.UNKNOWN_ERROR: 500,

        # 503 Service Unavailable
        ErrorCode.SERVICE_UNAVAILABLE: 503,
        ErrorCode.CONNECTION_POOL_EXHAUSTED: 503,

        # 504 Gateway Timeout
        ErrorCode.LLM_TIMEOUT: 504,
    }

    return status_mapping.get(error_code, 500)
