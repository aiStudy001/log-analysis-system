"""
Global Error Handling Middleware

Catches all unhandled exceptions and returns standardized error responses.
"""
import logging
import uuid
from datetime import datetime
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.models.errors import ErrorResponse, ErrorCode, get_http_status_for_error_code

logger = logging.getLogger(__name__)


async def error_handler_middleware(request: Request, call_next):
    """
    Global error handling middleware

    Intercepts all requests and catches unhandled exceptions,
    returning standardized error responses with request IDs.

    Args:
        request: FastAPI request object
        call_next: Next middleware/route handler

    Returns:
        Response with error details if exception occurred
    """
    # Generate unique request ID for tracing
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Add request ID to logger context
    logger_extra = {"request_id": request_id}

    try:
        response = await call_next(request)
        return response

    except RequestValidationError as e:
        # Handle Pydantic validation errors (400)
        logger.warning(
            f"Validation error for {request.method} {request.url.path}",
            extra=logger_extra,
            exc_info=True
        )

        error_response = ErrorResponse(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="요청 파라미터가 올바르지 않습니다",
            request_id=request_id,
            timestamp=datetime.now(),
            details={"errors": [{"loc": err["loc"], "msg": err["msg"], "type": err["type"]} for err in e.errors()]}
        )

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response.model_dump(mode='json')
        )

    except StarletteHTTPException as e:
        # Handle HTTP exceptions (various status codes)
        logger.warning(
            f"HTTP {e.status_code} error for {request.method} {request.url.path}: {e.detail}",
            extra=logger_extra
        )

        # Map HTTP status to error code
        error_code = _map_http_status_to_error_code(e.status_code)

        error_response = ErrorResponse(
            error_code=error_code,
            message=e.detail if isinstance(e.detail, str) else "요청 처리 중 오류가 발생했습니다",
            request_id=request_id,
            timestamp=datetime.now()
        )

        return JSONResponse(
            status_code=e.status_code,
            content=error_response.model_dump(mode='json')
        )

    except Exception as e:
        # Handle all other unhandled exceptions (500)
        logger.error(
            f"Unhandled exception for {request.method} {request.url.path}: {type(e).__name__}",
            extra=logger_extra,
            exc_info=True
        )

        error_response = ErrorResponse(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            request_id=request_id,
            timestamp=datetime.now(),
            details={"error_type": type(e).__name__}
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(mode='json')
        )


def _map_http_status_to_error_code(status_code: int) -> ErrorCode:
    """
    Map HTTP status codes to ErrorCode enum

    Args:
        status_code: HTTP status code

    Returns:
        Corresponding ErrorCode enum value
    """
    mapping = {
        400: ErrorCode.INVALID_REQUEST,
        404: ErrorCode.INVALID_REQUEST,
        422: ErrorCode.VALIDATION_ERROR,
        500: ErrorCode.INTERNAL_ERROR,
        503: ErrorCode.SERVICE_UNAVAILABLE,
        504: ErrorCode.LLM_TIMEOUT,
    }

    return mapping.get(status_code, ErrorCode.UNKNOWN_ERROR)
