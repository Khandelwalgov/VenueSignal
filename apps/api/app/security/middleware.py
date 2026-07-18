from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import RLock
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config import Settings


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = RLock()

    def _client_key(self, request: Request) -> str:
        if self.settings.trust_proxy_headers:
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                return forwarded.split(",", 1)[0].strip()
        return request.client.host if request.client else "unknown"

    def _rate_limited(self, request: Request) -> bool:
        if request.url.path in {"/health", "/ready"}:
            return False
        now = time.monotonic()
        cutoff = now - self.settings.rate_limit_window_seconds
        key = self._client_key(request)
        with self._lock:
            samples = self._requests[key]
            while samples and samples[0] <= cutoff:
                samples.popleft()
            if len(samples) >= self.settings.rate_limit_requests:
                return True
            samples.append(now)
            return False

    def _secure_response(self, request: Request, response: Response, request_id: str) -> Response:
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data:; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
            if request.url.path.startswith("/docs")
            else "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        response.headers["Cache-Control"] = "no-store"
        if self.settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id", "")[:80] or uuid4().hex
        content_length = request.headers.get("content-length")
        try:
            parsed_content_length = int(content_length) if content_length else None
            if parsed_content_length is not None and parsed_content_length < 0:
                raise ValueError
            oversized = parsed_content_length is not None and parsed_content_length > self.settings.max_request_bytes
        except ValueError:
            return self._secure_response(
                request,
                JSONResponse(status_code=400, content={"detail": "Invalid Content-Length", "requestId": request_id}),
                request_id,
            )
        if oversized:
            return self._secure_response(
                request,
                JSONResponse(status_code=413, content={"detail": "Request body is too large", "requestId": request_id}),
                request_id,
            )
        if self._rate_limited(request):
            return self._secure_response(
                request,
                JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(self.settings.rate_limit_window_seconds)},
                    content={"detail": "Rate limit exceeded", "requestId": request_id},
                ),
                request_id,
            )
        if request.method in {"POST", "PUT", "PATCH"}:
            chunks: list[bytes] = []
            received = 0
            async for chunk in request.stream():
                received += len(chunk)
                if received > self.settings.max_request_bytes:
                    return self._secure_response(
                        request,
                        JSONResponse(status_code=413, content={"detail": "Request body is too large", "requestId": request_id}),
                        request_id,
                    )
                chunks.append(chunk)
            request._body = b"".join(chunks)
        response = await call_next(request)
        return self._secure_response(request, response, request_id)
