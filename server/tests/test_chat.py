"""
Tests for routes/chat.py — private one-to-one chat REST endpoints.

All database access is mocked at the models.chat / models.user function
level (the same functions routes/chat.py imports), so these tests never
touch MySQL. Real-time behavior (sockets.py) isn't covered here since it
needs a live Socket.IO client — this suite is the REST/auth/validation
layer: conversation list, history pagination, search, delete, read
receipts, and access control (can't touch a conversation you're not in).
"""

import datetime

from utils.security import generate_token


def auth_header(user_id=1, email="test@example.com"):
    token = generate_token(user_id, email)
    return {"Authorization": f"Bearer {token}"}


def make_user(**overrides):
    user = {
        "id": 2,
        "name": "Other User",
        "email": "other@example.com",
        "profile_photo": None,
        "is_online": 1,
        "last_seen": datetime.datetime(2026, 1, 1),
    }
    user.update(overrides)
    return user


def make_message(**overrides):
    msg = {
        "id": 10,
        "conversation_id": 5,
        "sender_id": 1,
        "message_type": "text",
        "body": "Hello there",
        "attachment_url": None,
        "attachment_name": None,
        "created_at": datetime.datetime(2026, 1, 1, 12, 0, 0),
        "deleted_at": None,
    }
    msg.update(overrides)
    return msg


# ---------------------------------------------------
# GET /api/chat/conversations
# ---------------------------------------------------

def test_requires_auth(client):
    resp = client.get("/api/chat/conversations")
    assert resp.status_code == 401


def test_list_conversations(client, monkeypatch):
    monkeypatch.setattr(
        "routes.chat.chat_model.list_conversations_for_user",
        lambda user_id: [
            {
                "conversation_id": 5,
                "other_user": make_user(),
                "last_message": make_message(),
                "unread_count": 2,
            }
        ],
    )

    resp = client.get("/api/chat/conversations", headers=auth_header())
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["conversations"]) == 1
    convo = body["conversations"][0]
    assert convo["unread_count"] == 2
    assert convo["other_user"]["id"] == 2
    assert convo["last_message"]["body"] == "Hello there"


# ---------------------------------------------------
# POST /api/chat/conversations
# ---------------------------------------------------

def test_start_conversation(client, monkeypatch):
    monkeypatch.setattr("routes.chat.find_by_id", lambda uid: make_user(id=uid))
    monkeypatch.setattr(
        "routes.chat.chat_model.get_or_create_direct_conversation",
        lambda a, b: 42,
    )

    resp = client.post("/api/chat/conversations", json={"user_id": 2}, headers=auth_header())
    assert resp.status_code == 200
    assert resp.get_json()["conversation_id"] == 42


def test_start_conversation_with_self_rejected(client):
    resp = client.post("/api/chat/conversations", json={"user_id": 1}, headers=auth_header(user_id=1))
    assert resp.status_code == 400


def test_start_conversation_missing_user(client):
    resp = client.post("/api/chat/conversations", json={}, headers=auth_header())
    assert resp.status_code == 400


def test_start_conversation_unknown_user(client, monkeypatch):
    monkeypatch.setattr("routes.chat.find_by_id", lambda uid: None)
    resp = client.post("/api/chat/conversations", json={"user_id": 999}, headers=auth_header())
    assert resp.status_code == 404


# ---------------------------------------------------
# GET /api/chat/conversations/<id>/messages
# ---------------------------------------------------

def test_get_messages_not_a_participant(client, monkeypatch):
    monkeypatch.setattr("routes.chat.chat_model.is_participant", lambda cid, uid: False)
    resp = client.get("/api/chat/conversations/5/messages", headers=auth_header())
    assert resp.status_code == 404


def test_get_messages_success(client, monkeypatch):
    monkeypatch.setattr("routes.chat.chat_model.is_participant", lambda cid, uid: True)
    monkeypatch.setattr(
        "routes.chat.chat_model.list_messages",
        lambda conversation_id, before_id=None, limit=30: [make_message()],
    )
    monkeypatch.setattr("routes.chat.chat_model.get_read_state", lambda cid: {1: 10, 2: 9})

    resp = client.get("/api/chat/conversations/5/messages", headers=auth_header())
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["messages"]) == 1
    assert body["messages"][0]["body"] == "Hello there"
    assert body["read_state"] == {"1": 10, "2": 9} or body["read_state"] == {1: 10, 2: 9}


def test_get_messages_deleted_message_hides_body(client, monkeypatch):
    monkeypatch.setattr("routes.chat.chat_model.is_participant", lambda cid, uid: True)
    monkeypatch.setattr(
        "routes.chat.chat_model.list_messages",
        lambda conversation_id, before_id=None, limit=30: [
            make_message(deleted_at=datetime.datetime(2026, 1, 2))
        ],
    )
    monkeypatch.setattr("routes.chat.chat_model.get_read_state", lambda cid: {})

    resp = client.get("/api/chat/conversations/5/messages", headers=auth_header())
    body = resp.get_json()
    assert body["messages"][0]["deleted"] is True
    assert body["messages"][0]["body"] is None


# ---------------------------------------------------
# GET /api/chat/search
# ---------------------------------------------------

def test_search_requires_min_length(client):
    resp = client.get("/api/chat/search?q=a", headers=auth_header())
    assert resp.status_code == 400


def test_search_success(client, monkeypatch):
    monkeypatch.setattr(
        "routes.chat.chat_model.search_messages",
        lambda user_id, query, limit=50: [make_message(body="found it")],
    )
    resp = client.get("/api/chat/search?q=found", headers=auth_header())
    assert resp.status_code == 200
    assert resp.get_json()["results"][0]["body"] == "found it"


# ---------------------------------------------------
# DELETE /api/chat/messages/<id>
# ---------------------------------------------------

def test_delete_message_success(client, monkeypatch):
    monkeypatch.setattr("routes.chat.chat_model.soft_delete_message", lambda mid, uid: True)
    resp = client.delete("/api/chat/messages/10", headers=auth_header())
    assert resp.status_code == 200
    assert resp.get_json()["deleted"] is True


def test_delete_message_not_owned(client, monkeypatch):
    monkeypatch.setattr("routes.chat.chat_model.soft_delete_message", lambda mid, uid: False)
    resp = client.delete("/api/chat/messages/10", headers=auth_header())
    assert resp.status_code == 404


# ---------------------------------------------------
# POST /api/chat/conversations/<id>/read
# ---------------------------------------------------

def test_mark_read_requires_participant(client, monkeypatch):
    monkeypatch.setattr("routes.chat.chat_model.is_participant", lambda cid, uid: False)
    resp = client.post("/api/chat/conversations/5/read", json={"message_id": 10}, headers=auth_header())
    assert resp.status_code == 404


def test_mark_read_success(client, monkeypatch):
    monkeypatch.setattr("routes.chat.chat_model.is_participant", lambda cid, uid: True)
    monkeypatch.setattr("routes.chat.chat_model.mark_read", lambda cid, uid, mid: None)
    resp = client.post("/api/chat/conversations/5/read", json={"message_id": 10}, headers=auth_header())
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
