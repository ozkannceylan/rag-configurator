"""Tests for security utilities (no MongoDB required)."""

import pytest
from datetime import timedelta

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash prefix

    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test verifying incorrect password."""
        password = "mysecretpassword"
        hashed = get_password_hash(password)

        assert verify_password("wrongpassword", hashed) is False

    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        hash1 = get_password_hash("password1")
        hash2 = get_password_hash("password2")

        assert hash1 != hash2

    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "samepassword"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Hashes should be different due to different salts
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Tests for JWT token functions."""

    def test_create_access_token(self):
        """Test creating access token."""
        user_id = "user123"
        token = create_access_token(user_id)

        assert token is not None
        assert len(token) > 0
        assert isinstance(token, str)

    def test_create_refresh_token(self):
        """Test creating refresh token."""
        user_id = "user123"
        token = create_refresh_token(user_id)

        assert token is not None
        assert len(token) > 0
        assert isinstance(token, str)

    def test_decode_valid_access_token(self):
        """Test decoding valid access token."""
        user_id = "user123"
        token = create_access_token(user_id)
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "access"

    def test_decode_valid_refresh_token(self):
        """Test decoding valid refresh token."""
        user_id = "user456"
        token = create_refresh_token(user_id)
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self):
        """Test decoding invalid token returns None."""
        invalid_token = "invalid.token.here"
        payload = decode_token(invalid_token)

        assert payload is None

    def test_decode_tampered_token(self):
        """Test decoding tampered token returns None."""
        token = create_access_token("user123")
        # Tamper with the token
        tampered_token = token[:-5] + "xxxxx"
        payload = decode_token(tampered_token)

        assert payload is None

    def test_access_token_with_custom_expiry(self):
        """Test creating access token with custom expiry."""
        user_id = "user789"
        token = create_access_token(user_id, expires_delta=timedelta(hours=1))
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == user_id

    def test_refresh_token_with_custom_expiry(self):
        """Test creating refresh token with custom expiry."""
        user_id = "user789"
        token = create_refresh_token(user_id, expires_delta=timedelta(days=14))
        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == user_id


class TestTokenPayloadContents:
    """Tests for token payload contents."""

    def test_access_token_contains_required_fields(self):
        """Test access token contains all required fields."""
        token = create_access_token("testuser")
        payload = decode_token(token)

        assert "sub" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert "type" in payload
        assert payload["type"] == "access"

    def test_refresh_token_contains_required_fields(self):
        """Test refresh token contains all required fields."""
        token = create_refresh_token("testuser")
        payload = decode_token(token)

        assert "sub" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert "type" in payload
        assert payload["type"] == "refresh"

    def test_tokens_have_different_types(self):
        """Test that access and refresh tokens have different types."""
        access_token = create_access_token("user")
        refresh_token = create_refresh_token("user")

        access_payload = decode_token(access_token)
        refresh_payload = decode_token(refresh_token)

        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"
        assert access_payload["type"] != refresh_payload["type"]
