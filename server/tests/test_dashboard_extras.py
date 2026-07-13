"""
Tests for routes/user.py's dashboard additions: skills, education,
experience, settings (theme/privacy/notifications), the notification
center, the activity timeline, and the personal analytics summary.
All DB access is mocked at the models.profile_extras / models.user
function level — no live MySQL needed.
"""

from utils.security import generate_token


def auth_header(user_id=1, email="test@example.com"):
    token = generate_token(user_id, email)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------
# Skills
# ---------------------------------------------------

def test_list_skills(client, monkeypatch):
    monkeypatch.setattr(
        "routes.user.extras.list_skills",
        lambda uid: [{"id": 1, "name": "Python", "level": 5}],
    )
    resp = client.get("/api/user/skills", headers=auth_header())
    assert resp.status_code == 200
    assert resp.get_json()["skills"][0]["name"] == "Python"


def test_add_skill_validates_name(client):
    resp = client.post("/api/user/skills", json={"name": "", "level": 3}, headers=auth_header())
    assert resp.status_code == 400


def test_add_skill_clamps_level(client, monkeypatch):
    monkeypatch.setattr("routes.user.extras.add_skill", lambda uid, name, level: 10)
    monkeypatch.setattr("routes.user.extras.log_activity", lambda *a, **k: None)
    resp = client.post("/api/user/skills", json={"name": "Rust", "level": 99}, headers=auth_header())
    assert resp.status_code == 201
    assert resp.get_json()["level"] == 5  # clamped to max


def test_delete_skill_not_found(client, monkeypatch):
    monkeypatch.setattr("routes.user.extras.delete_skill", lambda sid, uid: False)
    resp = client.delete("/api/user/skills/99", headers=auth_header())
    assert resp.status_code == 404


# ---------------------------------------------------
# Education
# ---------------------------------------------------

def test_add_education_requires_school(client):
    resp = client.post("/api/user/education", json={"school": ""}, headers=auth_header())
    assert resp.status_code == 400


def test_add_education_success(client, monkeypatch):
    monkeypatch.setattr("routes.user.extras.add_education", lambda uid, **f: 7)
    monkeypatch.setattr("routes.user.extras.log_activity", lambda *a, **k: None)
    resp = client.post(
        "/api/user/education",
        json={"school": "IIT Patna", "degree": "B.Tech", "start_year": 2021, "end_year": 2025},
        headers=auth_header(),
    )
    assert resp.status_code == 201
    assert resp.get_json()["school"] == "IIT Patna"


def test_add_education_rejects_bad_year(client):
    resp = client.post(
        "/api/user/education",
        json={"school": "IIT Patna", "start_year": "not-a-number"},
        headers=auth_header(),
    )
    assert resp.status_code == 400


# ---------------------------------------------------
# Experience
# ---------------------------------------------------

def test_add_experience_requires_company_and_role(client):
    resp = client.post("/api/user/experience", json={"company": "", "role": ""}, headers=auth_header())
    assert resp.status_code == 400


def test_add_experience_current_clears_end_date(client, monkeypatch):
    captured = {}

    def fake_add(uid, **fields):
        captured.update(fields)
        return 3

    monkeypatch.setattr("routes.user.extras.add_experience", fake_add)
    monkeypatch.setattr("routes.user.extras.log_activity", lambda *a, **k: None)

    resp = client.post(
        "/api/user/experience",
        json={"company": "Acme", "role": "Intern", "is_current": True, "end_date": "2026-01-01"},
        headers=auth_header(),
    )
    assert resp.status_code == 201
    assert captured["end_date"] is None
    assert captured["is_current"] is True


# ---------------------------------------------------
# Settings
# ---------------------------------------------------

def test_update_theme_rejects_invalid_value(client):
    resp = client.put("/api/user/settings/theme", json={"theme": "rainbow"}, headers=auth_header())
    assert resp.status_code == 400


def test_update_theme_success(client, monkeypatch):
    monkeypatch.setattr("routes.user.update_settings", lambda uid, **f: {"id": uid, "name": "T", "email": "t@t.com", "theme": "light", "created_at": None})
    monkeypatch.setattr("routes.user.extras.log_activity", lambda *a, **k: None)
    resp = client.put("/api/user/settings/theme", json={"theme": "light"}, headers=auth_header())
    assert resp.status_code == 200
    assert resp.get_json()["user"]["theme"] == "light"


def test_update_privacy_rejects_invalid_value(client):
    resp = client.put("/api/user/settings/privacy", json={"profile_visibility": "hidden"}, headers=auth_header())
    assert resp.status_code == 400


def test_update_notifications_requires_a_field(client):
    resp = client.put("/api/user/settings/notifications", json={}, headers=auth_header())
    assert resp.status_code == 400


# ---------------------------------------------------
# Notification center
# ---------------------------------------------------

def test_list_notifications(client, monkeypatch):
    monkeypatch.setattr(
        "routes.user.extras.list_notifications",
        lambda uid: [{"id": 1, "type": "chat", "title": "New message", "body": None, "link": None, "is_read": 0, "created_at": None}],
    )
    monkeypatch.setattr("routes.user.extras.count_unread_notifications", lambda uid: 1)
    resp = client.get("/api/user/notifications", headers=auth_header())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["unread_count"] == 1
    assert body["notifications"][0]["title"] == "New message"


def test_mark_notification_read_not_found(client, monkeypatch):
    monkeypatch.setattr("routes.user.extras.mark_notification_read", lambda nid, uid: False)
    resp = client.put("/api/user/notifications/5/read", headers=auth_header())
    assert resp.status_code == 404


def test_mark_all_notifications_read(client, monkeypatch):
    monkeypatch.setattr("routes.user.extras.mark_all_notifications_read", lambda uid: None)
    resp = client.put("/api/user/notifications/read-all", headers=auth_header())
    assert resp.status_code == 200


# ---------------------------------------------------
# Activity timeline
# ---------------------------------------------------

def test_get_activity(client, monkeypatch):
    monkeypatch.setattr(
        "routes.user.extras.list_activity",
        lambda uid: [{"id": 1, "action": "login", "meta": None, "created_at": None}],
    )
    resp = client.get("/api/user/activity", headers=auth_header())
    assert resp.status_code == 200
    assert resp.get_json()["activity"][0]["action"] == "login"


# ---------------------------------------------------
# Dashboard analytics summary
# ---------------------------------------------------

def test_dashboard_summary(client, monkeypatch):
    monkeypatch.setattr("routes.user.find_by_id", lambda uid: {"id": uid, "created_at": None, "bio": "hi", "profile_photo": "/x.jpg"})
    monkeypatch.setattr("routes.user.project_model.list_by_user", lambda uid: [1, 2])
    monkeypatch.setattr("routes.user.extras.list_skills", lambda uid: [1, 2, 3])
    monkeypatch.setattr("routes.user.contact_model.list_by_user", lambda uid: [])
    monkeypatch.setattr("routes.user.chatbot_model.list_by_user", lambda uid: [1])
    monkeypatch.setattr("routes.user.chat_model.list_conversations_for_user", lambda uid: [])
    monkeypatch.setattr("routes.user.extras.count_unread_notifications", lambda uid: 2)

    resp = client.get("/api/user/dashboard/summary", headers=auth_header())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["projects"] == 2
    assert body["skills"] == 3
    assert body["unread_notifications"] == 2
    assert body["profile_complete"] is True
