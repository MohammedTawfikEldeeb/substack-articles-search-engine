import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.utils.logger_util import setup_logging

logger = setup_logging()


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_host = request.client.host if request.client else "unknown"

        safe_headers = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in {"authorization", "cookie"}
        }

        logger.info(
            f"Incoming request: {request.method} {request.url} from {client_host} "
            f"headers={safe_headers}"
        )

        try:
            response = await call_next(request)
        except Exception:
            duration = (time.time() - start_time) * 1000
            logger.exception(
                f"Request failed: {request.method} {request.url} from {client_host} "
                f"duration={duration:.2f}ms"
            )
            raise

        duration = (time.time() - start_time) * 1000
        logger.info(
            f"Completed request: {request.method} {request.url} from {client_host} "
            f"status_code={response.status_code} duration={duration:.2f}ms"
        )
        return response
