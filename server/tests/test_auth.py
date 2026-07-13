"""
Tests for routes/auth.py — signup, login, and the /me endpoint.

All database access is mocked at the models.user function level (the
same functions routes/auth.py imports), so these tests never touch
MySQL. They verify request validation, status codes, and the auth
flow logic itself.
"""

import datetime

from utils.security import hash_password, generate_token


def make_user(**overrides):
    """A fake row shaped like what models.user.find_by_email/find_by_id
    would return from the real `users` table."""
    user = {
        "id": 1,
        "name": "Test User",
        "email": "test@example.com",
        "password": hash_password("correct-password"),
        "profile_photo": None,
        "bio": None,
        "resume": None,
        "certificate": None,
        "role": "user",
        "is_banned": 0,
        "created_at": datetime.datetime(2026, 1, 1),
    }
    user.update(overrides)
    return user


# ---------------------------------------------------
# POST /api/auth/signup
# ---------------------------------------------------

def test_signup_success(client, monkeypatch):
    monkeypatch.setattr("routes.auth.find_by_email", lambda email: None)
    monkeypatch.setattr("routes.auth.create_user", lambda name, email, password_hash, role="user": make_user(
        name=name, email=email, role=role
    ))

    resp = client.post("/api/auth/signup", json={
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "supersecret",
    })

    assert resp.status_code == 201
    body = resp.get_json()
    assert "token" in body
    assert body["user"]["email"] == "jane@example.com"
    # The password hash must never be echoed back to the client.
    assert "password" not in body["user"]


def test_signup_rejects_short_name(client):
    resp = client.post("/api/auth/signup", json={
        "name": "J",
        "email": "jane@example.com",
        "password": "supersecret",
    })
    assert resp.status_code == 400
    assert "name" in resp.get_json()["error"].lower()


def test_signup_rejects_invalid_email(client):
    resp = client.post("/api/auth/signup", json={
        "name": "Jane Doe",
        "email": "not-an-email",
        "password": "supersecret",
    })
    assert resp.status_code == 400


def test_signup_rejects_short_password(client):
    resp = client.post("/api/auth/signup", json={
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "abc",
    })
    assert resp.status_code == 400


def test_signup_rejects_duplicate_email(client, monkeypatch):
    monkeypatch.setattr("routes.auth.find_by_email", lambda email: make_user(email=email))

    resp = client.post("/api/auth/signup", json={
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "supersecret",
    })
    assert resp.status_code == 409


# ---------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------

def test_login_success(client, monkeypatch):
    user = make_user()
    monkeypatch.setattr("routes.auth.find_by_email", lambda email: user)

    resp = client.post("/api/auth/login", json={
        "email": user["email"],
        "password": "correct-password",
    })

    assert resp.status_code == 200
    body = resp.get_json()
    assert "token" in body
    assert body["user"]["email"] == user["email"]


def test_login_wrong_password(client, monkeypatch):
    user = make_user()
    monkeypatch.setattr("routes.auth.find_by_email", lambda email: user)

    resp = client.post("/api/auth/login", json={
        "email": user["email"],
        "password": "totally-wrong",
    })
    assert resp.status_code == 401


def test_login_unknown_email(client, monkeypatch):
    monkeypatch.setattr("routes.auth.find_by_email", lambda email: None)

    resp = client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "whatever123",
    })
    assert resp.status_code == 401


def test_login_rejects_banned_account(client, monkeypatch):
    user = make_user(is_banned=1)
    monkeypatch.setattr("routes.auth.find_by_email", lambda email: user)

    resp = client.post("/api/auth/login", json={
        "email": user["email"],
        "password": "correct-password",
    })
    assert resp.status_code == 403


def test_login_wrong_password_and_unknown_email_give_same_error(client, monkeypatch):
    """Regression guard for the intentional anti-enumeration behavior:
    both cases must return the exact same message, or an attacker could
    use the response to figure out which emails are registered."""
    monkeypatch.setattr("routes.auth.find_by_email", lambda email: None)
    resp_unknown = client.post("/api/auth/login", json={
        "email": "nobody@example.com", "password": "whatever123",
    })

    user = make_user()
    monkeypatch.setattr("routes.auth.find_by_email", lambda email: user)
    resp_wrong_pw = client.post("/api/auth/login", json={
        "email": user["email"], "password": "totally-wrong",
    })

    assert resp_unknown.get_json()["error"] == resp_wrong_pw.get_json()["error"]


# ---------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------

def test_me_requires_auth_header(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_rejects_garbage_token(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_me_returns_current_user(client, monkeypatch):
    user = make_user()
    token = generate_token(user["id"], user["email"])
    monkeypatch.setattr("routes.auth.find_by_id", lambda user_id: user)

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["user"]["email"] == user["email"]
