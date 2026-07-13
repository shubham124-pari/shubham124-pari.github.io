"""
Unit tests for utils/privacy.py — the single source of truth for who can
see a profile or a post. are_connected() is monkeypatched (it's a DB
call), so these are pure logic tests.
"""

from utils import privacy


def make_user(**overrides):
    user = {"id": 1, "profile_visibility": "public"}
    user.update(overrides)
    return user


def make_post(**overrides):
    post = {"user_id": 1, "visibility": "public"}
    post.update(overrides)
    return post


# ---------------------------------------------------
# Profiles
# ---------------------------------------------------

def test_owner_always_sees_own_profile_even_if_private():
    user = make_user(id=5, profile_visibility="private")
    assert privacy.can_view_profile(5, user) is True


def test_public_profile_visible_to_anyone_including_anonymous():
    user = make_user(profile_visibility="public")
    assert privacy.can_view_profile(None, user) is True
    assert privacy.can_view_profile(999, user) is True


def test_private_profile_hidden_from_everyone_but_owner():
    user = make_user(id=5, profile_visibility="private")
    assert privacy.can_view_profile(None, user) is False
    assert privacy.can_view_profile(999, user) is False


def test_connections_only_profile_hidden_from_anonymous():
    user = make_user(id=5, profile_visibility="connections_only")
    assert privacy.can_view_profile(None, user) is False


def test_connections_only_profile_visible_to_connection(monkeypatch):
    monkeypatch.setattr(privacy, "are_connected", lambda a, b: True)
    user = make_user(id=5, profile_visibility="connections_only")
    assert privacy.can_view_profile(999, user) is True


def test_connections_only_profile_hidden_from_non_connection(monkeypatch):
    monkeypatch.setattr(privacy, "are_connected", lambda a, b: False)
    user = make_user(id=5, profile_visibility="connections_only")
    assert privacy.can_view_profile(999, user) is False


def test_unrecognized_visibility_value_fails_closed():
    user = make_user(profile_visibility="something-new-and-unknown")
    assert privacy.can_view_profile(999, user) is False


def test_missing_profile_returns_false():
    assert privacy.can_view_profile(1, None) is False


# ---------------------------------------------------
# Posts
# ---------------------------------------------------

def test_author_always_sees_own_post_even_if_private():
    post = make_post(user_id=5, visibility="private")
    assert privacy.can_view_post(5, post) is True


def test_public_post_visible_to_anonymous():
    post = make_post(visibility="public")
    assert privacy.can_view_post(None, post) is True


def test_private_post_hidden_from_everyone_but_author():
    post = make_post(user_id=5, visibility="private")
    assert privacy.can_view_post(None, post) is False
    assert privacy.can_view_post(999, post) is False


def test_connections_only_post_hidden_from_anonymous():
    post = make_post(visibility="connections_only")
    assert privacy.can_view_post(None, post) is False


def test_connections_only_post_visible_to_connection(monkeypatch):
    monkeypatch.setattr(privacy, "are_connected", lambda a, b: True)
    post = make_post(user_id=5, visibility="connections_only")
    assert privacy.can_view_post(999, post) is True


def test_can_view_files_matches_profile_rule():
    user = make_user(id=5, profile_visibility="private")
    assert privacy.can_view_files(None, user) is False
    assert privacy.can_view_files(5, user) is True
