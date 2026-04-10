"""FastAPI request-auth middleware for gateway-signed service requests."""

from __future__ import annotations

from typing import Awaitable, Callable

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from rag_config_common.auth.hmac_verify import (
    DEFAULT_MAX_AGE_SECONDS,
    SERVICE_SIGNATURE_HEADER,
    SERVICE_TIMESTAMP_HEADER,
    HMACVerificationError,
    verify_request_signature,
)


async def verify_request_auth(
    request: Request,
    *,
    secret: str,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> str | None:
    """Verify that an inbound request came through the trusted gateway."""
    body = await request.body()
    verify_request_signature(
        secret=secret,
        method=request.method,
        path=request.url.path,
        body=body,
        timestamp=request.headers.get(SERVICE_TIMESTAMP_HEADER),
        signature=request.headers.get(SERVICE_SIGNATURE_HEADER),
        max_age_seconds=max_age_seconds,
    )
    user_id = request.headers.get("X-User-ID")
    request.state.user_id = user_id
    return user_id


def get_authenticated_user_id(request: Request) -> str:
    """Return the gateway-authenticated user ID set by ServiceAuthMiddleware.

    Only trusts ``request.state.user_id`` which is written after HMAC
    verification succeeds.  Never falls back to raw request headers to
    prevent header-injection if the middleware is accidentally bypassed.
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authenticated user context",
        )
    return user_id


class ServiceAuthMiddleware(BaseHTTPMiddleware):
    """Require HMAC-signed gateway requests for service API routes."""

    def __init__(
        self,
        app,
        *,
        secret: str,
        api_prefix: str = "/api/",
        max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    ) -> None:
        super().__init__(app)
        self.secret = secret
        self.api_prefix = api_prefix
        self.max_age_seconds = max_age_seconds

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable],
    ):
        if request.method == "OPTIONS":
            return await call_next(request)
        if not request.url.path.startswith(self.api_prefix):
            return await call_next(request)

        if not self.secret:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "INTER_SERVICE_SECRET is not configured",
                },
            )

        try:
            await verify_request_auth(
                request,
                secret=self.secret,
                max_age_seconds=self.max_age_seconds,
            )
        except HMACVerificationError as exc:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": str(exc)},
            )

        return await call_next(request)
