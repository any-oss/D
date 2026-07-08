"""
Request Tracing Middleware
Injects X-Request-ID for distributed tracing and log correlation.
"""
import uuid
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from core.logging_config import get_logger

logger = get_logger(__name__)


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request tracing with unique IDs."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Add to request state for use in handlers
        request.state.request_id = request_id
        
        # Execute the request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        # Log request completion
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code}",
            extra={"request_id": request_id}
        )
        
        return response


def setup_tracing_middleware(app):
    """Add tracing middleware to FastAPI app."""
    app.add_middleware(RequestTracingMiddleware)
    logger.info("Request tracing middleware enabled")
