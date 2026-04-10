"""Shared authentication and request-auth utilities."""

from rag_config_common.auth.hmac_verify import (
    DEFAULT_MAX_AGE_SECONDS,
    SERVICE_SIGNATURE_HEADER,
    SERVICE_TIMESTAMP_HEADER,
    HMACVerificationError,
    InvalidSignatureError,
    InvalidTimestampError,
    MissingSignatureError,
    build_signed_headers,
    compute_body_hash,
    sign_request,
    verify_request_signature,
)
from rag_config_common.auth.jwt_utils import (
    decode_token,
    extract_bearer_token,
    get_token_jti,
    get_token_ttl_seconds,
    get_token_type,
    get_token_subject,
    verify_token_type,
)
from rag_config_common.auth.middleware import (
    ServiceAuthMiddleware,
    get_authenticated_user_id,
    verify_request_auth,
)
from rag_config_common.auth.token_blacklist import TokenBlacklist

__all__ = [
    "DEFAULT_MAX_AGE_SECONDS",
    "SERVICE_SIGNATURE_HEADER",
    "SERVICE_TIMESTAMP_HEADER",
    "HMACVerificationError",
    "InvalidSignatureError",
    "InvalidTimestampError",
    "MissingSignatureError",
    "build_signed_headers",
    "compute_body_hash",
    "sign_request",
    "verify_request_signature",
    "decode_token",
    "extract_bearer_token",
    "get_token_jti",
    "get_token_ttl_seconds",
    "get_token_type",
    "get_token_subject",
    "verify_token_type",
    "ServiceAuthMiddleware",
    "get_authenticated_user_id",
    "verify_request_auth",
    "TokenBlacklist",
]
