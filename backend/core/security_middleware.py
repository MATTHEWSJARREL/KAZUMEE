"""
Security middleware for FastAPI application.
Adds security headers, request/response validation, and HTTPS enforcement.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging
import os

logger = logging.getLogger(__name__)

IS_PROD = os.getenv("ENV", "development").lower() == "production"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=(), payment=()"

        if IS_PROD:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self' 'unsafe-eval'; "
                "script-src 'self' 'unsafe-eval' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' ws: wss:"
            )

        # Remove sensitive headers
        response.headers.pop("Server", None)

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log requests for security monitoring"""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Don't log auth tokens or sensitive headers
        headers_to_log = {k: v for k, v in request.headers.items() if k.lower() not in ('authorization', 'cookie')}

        logger.info(
            f"REQUEST: {request.method} {request.url.path} | "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )

        try:
            response = await call_next(request)
            logger.info(f"RESPONSE: {request.method} {request.url.path} | Status: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"REQUEST ERROR: {request.method} {request.url.path} | Error: {str(e)}")
            raise


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP to HTTPS in production"""

    async def dispatch(self, request: Request, call_next) -> Response:
        if IS_PROD and request.url.scheme == "http":
            # Only redirect if not from health check
            if request.url.path not in ("/health", "/monitoring/health"):
                logger.warning(f"Redirecting HTTP to HTTPS: {request.url}")
                return Response(
                    status_code=307,
                    headers={"Location": request.url.replace("http://", "https://")}
                )

        return await call_next(request)


class RateLimitExceededMiddleware(BaseHTTPMiddleware):
    """Enhanced rate limit error responses"""

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            if "rate limit" in str(e).lower():
                logger.warning(f"Rate limit exceeded for {request.client.host}: {request.url.path}")
                return Response(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please try again later."},
                    media_type="application/json"
                )
            raise
