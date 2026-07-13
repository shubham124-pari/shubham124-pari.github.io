import re
from flask import Blueprint, request, jsonify, g

from models.project import list_by_user, create_project, update_project, delete_project
from models.profile_extras import log_activity
from utils.security import token_required
from utils.serializers import project_public

project_bp = Blueprint("project", __name__, url_prefix="/api/projects")

# Only accept image URLs that point at a file our own upload endpoint
# created — never an attacker-supplied arbitrary URL string.
PROJECT_IMAGE_RE = re.compile(r"^/uploads/projects/[a-f0-9]{32}\.(jpg|png)$")
URL_RE = re.compile(r"^https?://[^\s]+$")


def _parse_and_validate(data: dict):
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    image = (data.get("image") or "").strip()
    github = (data.get("github") or "").strip()
    demo = (data.get("demo") or "").strip()

    if len(title) < 2 or len(title) > 150:
        return None, "Title must be between 2 and 150 characters."
    if len(description) > 2000:
        return None, "Description must be under 2000 characters."
    if image and not PROJECT_IMAGE_RE.match(image):
        return None, "Invalid image — upload one via /api/user/upload/project first."
    if github and (len(github) > 255 or not URL_RE.match(github)):
        return None, "GitHub link must be a valid http(s) URL under 255 characters."
    if demo and (len(demo) > 255 or not URL_RE.match(demo)):
        return None, "Demo link must be a valid http(s) URL under 255 characters."

    return {
        "title": title,
        "description": description or None,
        "image": image or None,
        "github": github or None,
        "demo": demo or None,
    }, None


@project_bp.get("")
@token_required
def get_projects():
    projects = list_by_user(g.user_id)
    return jsonify({"projects": [project_public(p) for p in projects]}), 200


@project_bp.post("")
@token_required
def add_project():
    data = request.get_json(silent=True) or {}
    fields, error = _parse_and_validate(data)
    if error:
        return jsonify({"error": error}), 400

    project = create_project(g.user_id, **fields)
    log_activity(g.user_id, "project_create", fields["title"])
    return jsonify({"project": project_public(project)}), 201


@project_bp.put("/<int:project_id>")
@token_required
def edit_project(project_id):
    data = request.get_json(silent=True) or {}
    fields, error = _parse_and_validate(data)
    if error:
        return jsonify({"error": error}), 400

    project = update_project(project_id, g.user_id, **fields)
    if not project:
        return jsonify({"error": "Project not found."}), 404
    log_activity(g.user_id, "project_update", fields["title"])
    return jsonify({"project": project_public(project)}), 200


@project_bp.delete("/<int:project_id>")
@token_required
def remove_project(project_id):
    deleted = delete_project(project_id, g.user_id)
    if not deleted:
        return jsonify({"error": "Project not found."}), 404
    log_activity(g.user_id, "project_delete", str(project_id))
    return jsonify({"message": "Project deleted."}), 200
