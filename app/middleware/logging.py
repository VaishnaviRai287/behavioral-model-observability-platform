import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("modelmesh.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every HTTP request as structured JSON.

    Emits one log line per request containing:
    - request_id: unique UUID per request (for log correlation)
    - method: HTTP verb (GET, POST, etc.)
    - path: URL path
    - status_code: HTTP response code
    - duration_ms: total request time including handler
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000

        log_entry = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        }
        logger.info(json.dumps(log_entry))

        return response
