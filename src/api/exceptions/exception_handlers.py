from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from qdrant_client.http.exceptions import UnexpectedResponse

from src.utils.logger_util import setup_logging

logger = setup_logging()


async def validation_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    if isinstance(exc, RequestValidationError):
        logger.warning(f"Validation error on {request.url}: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "type": "validation_error",
                "message": "Invalid request",
                "details": exc.errors(),
            },
        )

    logger.exception(f"Unexpected exception on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "type": "internal_error",
            "message": "Internal server error",
            "details": str(exc),
        },
    )


async def qdrant_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, UnexpectedResponse):
        logger.error(f"Qdrant error on {request.url}: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "type": "qdrant_error",
                "message": "Vector store error",
                "details": str(exc),
            },
        )

    logger.exception(f"Unexpected exception on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "type": "internal_error",
            "message": "Internal server error",
            "details": str(exc),
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled exception on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "type": "internal_error",
            "message": "Internal server error",
            "details": str(exc),
        },
    )
