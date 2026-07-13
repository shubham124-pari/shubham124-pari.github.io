"""
Unit tests for utils/security.py — password hashing and JWT helpers.
Pure unit tests, no Flask app or database involved.
"""

import datetime
import jwt as pyjwt
import pytest

from config import Config
from utils.security import (
    hash_password,
    verify_password,
    generate_token,
    decode_token,
)


def test_hash_password_does_not_store_plaintext():
    hashed = hash_password("my-secret-password")
    assert hashed != "my-secret-password"
    assert len(hashed) > 20


def test_verify_password_accepts_correct_password():
    hashed = hash_password("my-secret-password")
    assert verify_password("my-secret-password", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("my-secret-password")
    assert verify_password("wrong-password", hashed) is False


def test_same_password_hashes_differently_each_time():
    # Salted hashing: two hashes of the same password must not be equal,
    # otherwise identical passwords would be visibly identical in the DB.
    hash_a = hash_password("my-secret-password")
    hash_b = hash_password("my-secret-password")
    assert hash_a != hash_b


def test_generate_and_decode_token_roundtrip():
    token = generate_token(user_id=42, email="test@example.com")
    payload = decode_token(token)
    assert payload["sub"] == 42
    assert payload["email"] == "test@example.com"


def test_decode_token_rejects_garbage():
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_token("this-is-not-a-jwt")


def test_decode_token_rejects_expired_token():
    expired_payload = {
        "sub": 1,
        "email": "test@example.com",
        "iat": datetime.datetime.utcnow() - datetime.timedelta(hours=2),
        "exp": datetime.datetime.utcnow() - datetime.timedelta(hours=1),
    }
    expired_token = pyjwt.encode(expired_payload, Config.JWT_SECRET_KEY, algorithm="HS256")

    with pytest.raises(pyjwt.ExpiredSignatureError):
        decode_token(expired_token)


def test_decode_token_rejects_wrong_secret():
    token = pyjwt.encode(
        {
            "sub": 1,
            "email": "test@example.com",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        },
        "a-completely-different-secret",
        algorithm="HS256",
    )
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_token(token)
