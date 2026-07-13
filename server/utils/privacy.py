"""
Single source of truth for "can this viewer see this thing".

Every route that returns another user's profile, files, or posts MUST
route its decision through these two functions instead of re-implementing
the public/connections_only/private logic inline. That's what guarantees
a user can never see another user's private content: there is exactly one
place this gate is decided, and it fails closed (defaults to False) for
anything it doesn't explicitly recognize.
"""

from models.social import are_connected

VISIBILITY_LEVELS = {"public", "connections_only", "private"}


def can_view_profile(viewer_id, profile_user: dict) -> bool:
    """profile_user is the target account's row (must include id and
    profile_visibility). viewer_id is None for signed-out visitors."""
    if not profile_user:
        return False
    if viewer_id is not None and viewer_id == profile_user["id"]:
        return True  # owners always see their own profile

    visibility = profile_user.get("profile_visibility", "public")
    if visibility == "public":
        return True
    if visibility == "connections_only":
        return viewer_id is not None and are_connected(viewer_id, profile_user["id"])
    if visibility == "private":
        return False
    return False  # fail closed on any unrecognized value


def can_view_post(viewer_id, post: dict) -> bool:
    """post must include user_id and visibility."""
    if not post:
        return False
    if viewer_id is not None and viewer_id == post["user_id"]:
        return True  # authors always see their own posts

    visibility = post.get("visibility", "public")
    if visibility == "public":
        return True
    if visibility == "connections_only":
        return viewer_id is not None and are_connected(viewer_id, post["user_id"])
    if visibility == "private":
        return False
    return False  # fail closed


def can_view_files(viewer_id, profile_user: dict) -> bool:
    """Resume/certificate/uploaded files follow the same rule as the
    profile itself — a private or connections-only account's uploaded
    files are never exposed to a viewer who can't see the profile."""
    return can_view_profile(viewer_id, profile_user)
