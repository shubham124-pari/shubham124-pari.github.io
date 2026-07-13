"""
Route-level tests for routes/social.py, routes/post.py, routes/interaction.py.
All DB access is mocked at the models function level, same pattern as
tests/test_auth.py.
"""

import datetime
from utils.security import generate_token


def make_profile_row(**overrides):
    row = {
        "id": 2, "name": "Jane Doe", "username": "janedoe",
        "profile_photo": None, "bio": "hi", "profile_visibility": "public",
        "role": "user", "created_at": datetime.datetime(2026, 1, 1),
    }
    row.update(overrides)
    return row


def auth_header(user_id=1, email="me@example.com"):
    return {"Authorization": f"Bearer {generate_token(user_id, email)}"}


# ---------------------------------------------------
# GET /api/social/profile/<username> — the core privacy gate
# ---------------------------------------------------

def test_public_profile_visible_to_signed_out_visitor(client, monkeypatch):
    monkeypatch.setattr("routes.social.find_by_username", lambda u: make_profile_row())
    monkeypatch.setattr("routes.social.count_followers", lambda uid: 0)
    monkeypatch.setattr("routes.social.count_following", lambda uid: 0)

    res = client.get("/api/social/profile/janedoe")
    assert res.status_code == 200
    assert res.get_json()["profile"]["username"] == "janedoe"


def test_private_profile_hidden_from_stranger(client, monkeypatch):
    monkeypatch.setattr(
        "routes.social.find_by_username",
        lambda u: make_profile_row(profile_visibility="private"),
    )
    res = client.get("/api/social/profile/janedoe", headers=auth_header(user_id=999))
    assert res.status_code == 403


def test_private_profile_visible_to_owner(client, monkeypatch):
    monkeypatch.setattr(
        "routes.social.find_by_username",
        lambda u: make_profile_row(id=1, profile_visibility="private"),
    )
    monkeypatch.setattr("routes.social.count_followers", lambda uid: 0)
    monkeypatch.setattr("routes.social.count_following", lambda uid: 0)

    res = client.get("/api/social/profile/janedoe", headers=auth_header(user_id=1))
    assert res.status_code == 200
    assert res.get_json()["profile"]["is_owner"] is True


def test_connections_only_profile_hidden_from_non_connection(client, monkeypatch):
    monkeypatch.setattr(
        "routes.social.find_by_username",
        lambda u: make_profile_row(profile_visibility="connections_only"),
    )
    monkeypatch.setattr("routes.social.are_connected", lambda a, b: False)
    res = client.get("/api/social/profile/janedoe", headers=auth_header(user_id=999))
    assert res.status_code == 403


def test_unknown_username_returns_404(client, monkeypatch):
    monkeypatch.setattr("routes.social.find_by_username", lambda u: None)
    res = client.get("/api/social/profile/nobody")
    assert res.status_code == 404


# ---------------------------------------------------
# Follow / unfollow
# ---------------------------------------------------

def test_cannot_follow_yourself(client):
    res = client.post("/api/social/follow/1", headers=auth_header(user_id=1))
    assert res.status_code == 400


def test_follow_requires_auth(client):
    res = client.post("/api/social/follow/2")
    assert res.status_code == 401


def test_follow_success(client, monkeypatch):
    monkeypatch.setattr("routes.social.find_by_id", lambda uid: make_profile_row(id=2), raising=False)
    monkeypatch.setattr("models.user.find_by_id", lambda uid: make_profile_row(id=2))
    monkeypatch.setattr("routes.social.follow_user", lambda a, b: True)
    res = client.post("/api/social/follow/2", headers=auth_header(user_id=1))
    assert res.status_code == 200
    assert res.get_json()["following"] is True


# ---------------------------------------------------
# Connection requests
# ---------------------------------------------------

def test_cannot_connect_with_yourself(client):
    res = client.post("/api/social/connections/request/1", headers=auth_header(user_id=1))
    assert res.status_code == 400


def test_connection_request_blocked_if_already_pending(client, monkeypatch):
    monkeypatch.setattr("models.user.find_by_id", lambda uid: make_profile_row(id=2))
    monkeypatch.setattr(
        "routes.social.find_connection_between",
        lambda a, b: {"status": "pending"},
    )
    res = client.post("/api/social/connections/request/2", headers=auth_header(user_id=1))
    assert res.status_code == 409


def test_only_addressee_can_accept_request(client, monkeypatch):
    # respond_to_connection itself enforces addressee_id in the WHERE
    # clause — simulate it returning False for a non-addressee caller.
    monkeypatch.setattr("routes.social.respond_to_connection", lambda rid, uid, accept: False)
    res = client.post("/api/social/connections/99/accept", headers=auth_header(user_id=1))
    assert res.status_code == 404


# ---------------------------------------------------
# Posts: create / edit / delete ownership
# ---------------------------------------------------

def make_post_row(**overrides):
    row = {
        "id": 10, "user_id": 1, "post_type": "text", "content": "hello",
        "media_url": None, "visibility": "public", "is_edited": 0,
        "created_at": datetime.datetime(2026, 1, 1), "updated_at": datetime.datetime(2026, 1, 1),
    }
    row.update(overrides)
    return row


def test_create_text_post_requires_content(client):
    res = client.post("/api/posts", json={"post_type": "text", "content": ""}, headers=auth_header())
    assert res.status_code == 400


def test_create_post_success(client, monkeypatch):
    monkeypatch.setattr("routes.post.create_post", lambda *a, **k: make_post_row())
    monkeypatch.setattr("routes.post.has_liked", lambda pid, uid: False)
    monkeypatch.setattr("routes.post.has_bookmarked", lambda pid, uid: False)
    monkeypatch.setattr("routes.post.count_likes", lambda pid: 0)
    monkeypatch.setattr("routes.post.count_comments", lambda pid: 0)
    monkeypatch.setattr("routes.post.count_shares", lambda pid: 0)

    res = client.post("/api/posts", json={"post_type": "text", "content": "hello world"}, headers=auth_header())
    assert res.status_code == 201
    assert res.get_json()["post"]["content"] == "hello"


def test_cannot_edit_someone_elses_post(client, monkeypatch):
    monkeypatch.setattr("routes.post.find_post_by_id", lambda pid: make_post_row(user_id=2))
    res = client.put("/api/posts/10", json={"content": "hacked"}, headers=auth_header(user_id=1))
    assert res.status_code == 403


def test_delete_post_not_owned_returns_404(client, monkeypatch):
    # delete_post scopes the DELETE to user_id at the SQL level — a
    # mismatched owner means 0 rows affected, surfaced here as False.
    monkeypatch.setattr("routes.post.delete_post", lambda pid, uid: False)
    res = client.delete("/api/posts/10", headers=auth_header(user_id=1))
    assert res.status_code == 404


# ---------------------------------------------------
# Post visibility enforcement on read
# ---------------------------------------------------

def test_private_post_hidden_from_other_user(client, monkeypatch):
    monkeypatch.setattr("routes.post.find_post_by_id", lambda pid: make_post_row(user_id=2, visibility="private"))
    res = client.get("/api/posts/10", headers=auth_header(user_id=1))
    assert res.status_code == 404


def test_private_post_visible_to_author(client, monkeypatch):
    monkeypatch.setattr("routes.post.find_post_by_id", lambda pid: make_post_row(user_id=1, visibility="private"))
    monkeypatch.setattr("routes.post.has_liked", lambda pid, uid: False)
    monkeypatch.setattr("routes.post.has_bookmarked", lambda pid, uid: False)
    monkeypatch.setattr("routes.post.count_likes", lambda pid: 0)
    monkeypatch.setattr("routes.post.count_comments", lambda pid: 0)
    monkeypatch.setattr("routes.post.count_shares", lambda pid: 0)

    res = client.get("/api/posts/10", headers=auth_header(user_id=1))
    assert res.status_code == 200


def test_posts_by_user_blocked_for_private_profile(client, monkeypatch):
    monkeypatch.setattr(
        "routes.post.find_by_username",
        lambda u: make_profile_row(id=2, profile_visibility="private"),
    )
    res = client.get("/api/posts/user/janedoe", headers=auth_header(user_id=999))
    assert res.status_code == 403


# ---------------------------------------------------
# Interactions can't be used to probe hidden posts
# ---------------------------------------------------

def test_cannot_like_a_private_post_you_cannot_see(client, monkeypatch):
    monkeypatch.setattr("routes.interaction.find_post_by_id", lambda pid: make_post_row(user_id=2, visibility="private"))
    res = client.post("/api/posts/10/like", headers=auth_header(user_id=1))
    assert res.status_code == 404


def test_can_like_own_private_post(client, monkeypatch):
    monkeypatch.setattr("routes.interaction.find_post_by_id", lambda pid: make_post_row(user_id=1, visibility="private"))
    monkeypatch.setattr("routes.interaction.like_post", lambda pid, uid: True)
    res = client.post("/api/posts/10/like", headers=auth_header(user_id=1))
    assert res.status_code == 200


def test_cannot_comment_on_post_you_cannot_see(client, monkeypatch):
    monkeypatch.setattr("routes.interaction.find_post_by_id", lambda pid: make_post_row(user_id=2, visibility="connections_only"))
    monkeypatch.setattr("routes.interaction.are_connected", lambda a, b: False, raising=False)
    monkeypatch.setattr("utils.privacy.are_connected", lambda a, b: False)
    res = client.post("/api/posts/10/comments", json={"content": "hi"}, headers=auth_header(user_id=1))
    assert res.status_code == 404
