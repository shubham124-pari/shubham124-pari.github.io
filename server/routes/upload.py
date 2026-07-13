import os
import uuid

from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError

from models.user import update_file_field
from models.profile_extras import log_activity
from utils.security import token_required

upload_bp = Blueprint("upload", __name__, url_prefix="/api/user")

UPLOAD_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

IMAGE_EXTS = {"jpg", "jpeg", "png"}

# url kind -> (allowed extensions, max size in bytes, DB column or None,
#              subfolder, resize dimension or None)
# column=None means "just return the URL, don't write it anywhere" — used
# by project images, since each project (not the user row) owns its image.
FILE_KINDS = {
    "resume": ({"pdf"}, 5 * 1024 * 1024, "resume", "resumes", None),
    "certificate": ({"pdf", "jpg", "jpeg", "png"}, 5 * 1024 * 1024, "certificate", "certificates", None),
    "photo": ({"jpg", "jpeg", "png"}, 3 * 1024 * 1024, "profile_photo", "photos", 512),
    "cover": ({"jpg", "jpeg", "png"}, 5 * 1024 * 1024, "cover_photo", "covers", 1600),
    "project": ({"jpg", "jpeg", "png"}, 4 * 1024 * 1024, None, "projects", 1000),
    # Chat attachments: column=None because the URL is attached to a
    # message (via the send_message socket event / models/chat.py),
    # not written to any column on the users table.
    "chat_image": ({"jpg", "jpeg", "png"}, 5 * 1024 * 1024, None, "chat", 1600),
    "chat_document": (
        {"pdf", "doc", "docx", "txt", "zip"}, 10 * 1024 * 1024, None, "chat", None,
    ),
    # Post media: column=None because the URL is attached to a post row
    # (via models/post.py), not written to any column on the users table.
    # Videos are never re-encoded/resized server-side (that needs ffmpeg,
    # which this stack deliberately doesn't depend on) — just validated
    # and stored as-is under a random name, same as resumes/certificates.
    "post_image": ({"jpg", "jpeg", "png"}, 5 * 1024 * 1024, None, "posts", 1600),
    "post_video": ({"mp4", "webm", "mov"}, 10 * 1024 * 1024, None, "posts", None),
}


def _ext(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _check_basics(file_storage, allowed_exts, max_bytes):
    """Filename/extension/size checks shared by every upload kind."""
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        return None, "No file selected."

    ext = _ext(filename)
    if ext not in allowed_exts:
        return None, f"Only {', '.join(sorted(allowed_exts))} files are allowed."

    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > max_bytes:
        return None, f"File too large. Max size is {max_bytes // (1024 * 1024)}MB."
    if size == 0:
        return None, "The uploaded file is empty."

    return ext, None


def _verify_real_image(file_storage):
    """Confirms the bytes are actually a decodable image (not just a file
    renamed to .jpg). Returns an error string, or None if it's genuine."""
    try:
        img = Image.open(file_storage.stream)
        img.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        return "The uploaded file is not a valid image."
    finally:
        file_storage.stream.seek(0)
    return None


def _save_resized_image(file_storage, folder, max_dimension):
    """Re-encodes the image: strips EXIF (which can contain GPS location),
    normalizes color mode, and shrinks it to at most max_dimension px on
    its longer side."""
    img = Image.open(file_storage.stream)
    img.load()

    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    img.thumbnail((max_dimension, max_dimension))

    # Re-saving from pixel data (instead of copying the original bytes)
    # is what actually drops the EXIF block — a fresh PNG/JPEG has none.
    is_transparent = img.mode == "RGBA"
    stored_name = f"{uuid.uuid4().hex}.{'png' if is_transparent else 'jpg'}"
    save_path = os.path.join(folder, stored_name)

    if is_transparent:
        img.save(save_path, "PNG")
    else:
        img.save(save_path, "JPEG", quality=85)

    return stored_name


def _save_raw(file_storage, folder, ext):
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(folder, stored_name))
    return stored_name


def _handle_upload(file_storage, allowed_exts, max_bytes, subfolder, resize_dimension):
    ext, error = _check_basics(file_storage, allowed_exts, max_bytes)
    if error:
        return None, error

    if ext in IMAGE_EXTS:
        error = _verify_real_image(file_storage)
        if error:
            return None, error

    folder = os.path.join(UPLOAD_ROOT, subfolder)
    os.makedirs(folder, exist_ok=True)

    if resize_dimension:
        stored_name = _save_resized_image(file_storage, folder, resize_dimension)
    else:
        stored_name = _save_raw(file_storage, folder, ext)

    return f"/uploads/{subfolder}/{stored_name}", None


@upload_bp.post("/upload/<kind>")
@token_required
def upload_file(kind):
    if kind not in FILE_KINDS:
        return jsonify({"error": "Unknown upload type."}), 400

    if "file" not in request.files:
        return jsonify({"error": "No file part in the request."}), 400

    allowed_exts, max_bytes, column, subfolder, resize_dimension = FILE_KINDS[kind]
    original_name = secure_filename(request.files["file"].filename or "")
    url_path, error = _handle_upload(
        request.files["file"], allowed_exts, max_bytes, subfolder, resize_dimension
    )
    if error:
        return jsonify({"error": error}), 400

    if column is None:
        # Project images and chat attachments: hand the URL back so the
        # caller (create/edit-project call, or the send_message socket
        # event) can attach it — nothing to write to the users table here.
        if kind in ("chat_image", "chat_document", "post_image", "post_video"):
            return jsonify({"url": url_path, "original_name": original_name}), 200
        return jsonify({"image": url_path}), 200

    user = update_file_field(g.user_id, column, url_path)
    if not user:
        return jsonify({"error": "User not found."}), 404

    log_activity(g.user_id, "file_upload", f"Uploaded {kind.replace('_', ' ')}")
    return jsonify({column: url_path}), 200
