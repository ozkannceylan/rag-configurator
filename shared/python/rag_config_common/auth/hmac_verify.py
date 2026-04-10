"""Shared HMAC signing and verification helpers for inter-service requests."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Mapping, MutableMapping, Optional


SERVICE_SIGNATURE_HEADER = "X-Service-Signature"
SERVICE_TIMESTAMP_HEADER = "X-Service-Timestamp"
DEFAULT_MAX_AGE_SECONDS = 30


class HMACVerificationError(ValueError):
    """Base error for request signature validation failures."""


class MissingSignatureError(HMACVerificationError):
    """Raised when signature headers are missing."""


class InvalidTimestampError(HMACVerificationError):
    """Raised when a request timestamp is invalid or outside the allowed skew."""


class InvalidSignatureError(HMACVerificationError):
    """Raised when a request signature does not match the expected value."""


def compute_body_hash(body: bytes | str | None) -> str:
    """Compute the SHA-256 hash used in HMAC request signing."""
    if body is None:
        body_bytes = b""
    elif isinstance(body, bytes):
        body_bytes = body
    else:
        body_bytes = body.encode("utf-8")
    return hashlib.sha256(body_bytes).hexdigest()


def _signature_payload(method: str, path: str, timestamp: int, body_hash: str) -> bytes:
    return f"{method.upper()}\n{path}\n{timestamp}\n{body_hash}".encode("utf-8")


def sign_request(
    secret: str,
    method: str,
    path: str,
    timestamp: int,
    body: bytes | str | None = None,
) -> str:
    """Create an HMAC-SHA256 signature for an outbound service request."""
    body_hash = compute_body_hash(body)
    payload = _signature_payload(method, path, timestamp, body_hash)
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def build_signed_headers(
    secret: str,
    method: str,
    path: str,
    body: bytes | str | None = None,
    *,
    timestamp: Optional[int] = None,
    user_id: Optional[str] = None,
) -> dict[str, str]:
    """Create signature headers suitable for a service-to-service HTTP request."""
    request_timestamp = timestamp or int(time.time())
    headers = {
        SERVICE_TIMESTAMP_HEADER: str(request_timestamp),
        SERVICE_SIGNATURE_HEADER: sign_request(
            secret=secret,
            method=method,
            path=path,
            timestamp=request_timestamp,
            body=body,
        ),
    }
    if user_id:
        headers["X-User-ID"] = user_id
    return headers


def verify_request_signature(
    secret: str,
    method: str,
    path: str,
    body: bytes | str | None,
    timestamp: str | int | None,
    signature: str | None,
    *,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    now: Optional[int] = None,
) -> None:
    """Validate an inbound service request signature."""
    if not signature or timestamp in (None, ""):
        raise MissingSignatureError("Missing service signature headers")

    try:
        request_timestamp = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise InvalidTimestampError("Invalid service timestamp") from exc

    current_time = now if now is not None else int(time.time())
    if abs(current_time - request_timestamp) > max_age_seconds:
        raise InvalidTimestampError("Service timestamp outside the allowed skew")

    expected = sign_request(
        secret=secret,
        method=method,
        path=path,
        timestamp=request_timestamp,
        body=body,
    )
    if not hmac.compare_digest(signature, expected):
        raise InvalidSignatureError("Invalid service signature")


def copy_signed_headers(
    headers: Mapping[str, str],
    target: MutableMapping[str, str],
) -> None:
    """Copy signature headers between request objects."""
    for header in (SERVICE_TIMESTAMP_HEADER, SERVICE_SIGNATURE_HEADER):
        if header in headers:
            target[header] = headers[header]
