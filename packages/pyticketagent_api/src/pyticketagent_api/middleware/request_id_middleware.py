"""Bind a per-request correlation ID so every log line in a request can be tied together."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from pyticketagent_core.observability.request_context import request_scope

_REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Bind ``X-Request-ID`` (incoming or generated) for the life of the request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        incoming = request.headers.get(_REQUEST_ID_HEADER)
        with request_scope(incoming) as request_id:
            response = await call_next(request)
            response.headers[_REQUEST_ID_HEADER] = request_id
            return response
