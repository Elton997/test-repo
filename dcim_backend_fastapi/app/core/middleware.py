"""
FastAPI middleware for logging API requests and responses with important debugging details.
"""
import time
import uuid
from typing import Any, Callable, Dict, Optional

import jwt
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logger import app_logger, set_request_context, clear_request_context
from app.core.config import settings


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log API requests and responses with structured JSON payloads.
    Automatically attaches a request_id to every request/response pair.
    """

    SENSITIVE_HEADERS = {
        "authorization",
        "x-auth-hash",
        "cookie",
        "x-api-key",
        "x-auth-token",
    }

    EXCLUDED_PATHS = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    MAX_BODY_LOG_BYTES = 10_000

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        set_request_context(
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
        )

        start_time = time.perf_counter()
        path = request.url.path
        is_excluded = path in self.EXCLUDED_PATHS or path.startswith("/static")

        if not is_excluded:
            await self._log_request(request, request_id)

        response: Optional[Response] = None
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            app_logger.exception(
                "Request failed with exception",
                extra={
                    "request_id": request_id,
                    "path": path,
                    "method": request.method,
                    "exception_type": type(exc).__name__,
                },
            )
            raise
        finally:
            process_time = (time.perf_counter() - start_time) * 1000
            if not is_excluded and response is not None:
                await self._log_response(request, response, request_id, process_time)
            clear_request_context()

    async def _log_request(self, request: Request, request_id: str) -> None:
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        headers = self._sanitize_headers(dict(request.headers))
        query_params = dict(request.query_params) if request.query_params else {}
        request_body = None

        if self._should_log_body(request):
            request_body = await self._extract_body(request)

        # Best-effort JWT extraction for logging/user context
        user_context = self._extract_user_from_jwt(request)
        if user_context and "user_id" in user_context:
            # Attach to request.state so downstream code can reuse it
            request.state.user_id = user_context["user_id"]

        log_func = app_logger.debug if settings.ENVIRONMENT in ("dev", "uat") else app_logger.info

        log_func(
            "API Request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": str(request.url.path),
                "query_params": query_params or None,
                "headers": headers,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "body": request_body,
                "user": user_context,
            },
        )

    async def _log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        process_time_ms: float,
    ) -> None:
        status_code = response.status_code
        if status_code >= 500:
            log_func = app_logger.error
        elif status_code >= 400:
            log_func = app_logger.warning
        else:
            log_func = app_logger.debug if settings.ENVIRONMENT in ("dev", "uat") else app_logger.info

        response_headers = self._sanitize_headers(dict(response.headers))

        log_func(
            "API Response",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": str(request.url.path),
                "status_code": status_code,
                "process_time_ms": round(process_time_ms, 2),
                "response_headers": response_headers if settings.ENVIRONMENT in ("dev", "uat") else None,
            },
        )

    async def _extract_body(self, request: Request) -> Optional[str]:
        try:
            body_bytes = await request.body()
        except Exception:
            return "<unable to read body>"

        if not body_bytes:
            return None

        if len(body_bytes) > self.MAX_BODY_LOG_BYTES:
            return f"<body too large: {len(body_bytes)} bytes>"

        try:
            body_text = body_bytes.decode("utf-8", errors="replace")
        except Exception:
            body_text = "<non-text body>"

        async def receive() -> Dict[str, Any]:
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        request._receive = receive  # type: ignore[attr-defined]
        return body_text

    def _should_log_body(self, request: Request) -> bool:
        if request.method not in ("POST", "PUT", "PATCH"):
            return False

        content_type = request.headers.get("content-type", "")
        if not content_type:
            return False

        disallowed_types = ("multipart/form-data", "application/octet-stream")
        return not any(ct in content_type for ct in disallowed_types)

    def _sanitize_headers(self, headers: Dict[str, Any]) -> Dict[str, Any]:
        sanitized: Dict[str, Any] = {}
        for key, value in headers.items():
            if key.lower() in self.SENSITIVE_HEADERS:
                sanitized[key] = "<redacted>"
            else:
                sanitized[key] = value
        return sanitized

    def _extract_user_from_jwt(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Extract user information from a JWT access token in the Authorization header.

        This performs a soft validation:
        - If token is valid, returns a small dict with user_id/username/roles.
        - If missing/invalid, returns None or an error descriptor – it does NOT
          raise, leaving actual auth enforcement to dependencies.
        """
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return None

        scheme, _, token = auth_header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return None

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except jwt.ExpiredSignatureError:
            return {"error": "expired"}
        except jwt.InvalidTokenError:
            return {"error": "invalid"}

        return {
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "roles": payload.get("roles"),
        }
