"""
sockets.py
=====================================================
Real-time half of the private chat feature, built on
Flask-SocketIO. The REST blueprint (routes/chat.py) handles
page-load data (conversation list, history, search); this
module handles everything that needs to be pushed live:

  - presence (online/offline, broadcast to the people you've
    chatted with)
  - typing indicators
  - new messages appearing instantly for both participants
  - read receipts
  - live delete notifications

Auth: the client connects with the JWT it already has from
login, sent as `auth: { token }` in the Socket.IO client
config (falls back to `?token=...` or an Authorization
header). There is no separate socket login step.
=====================================================
"""

import logging

from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request

import models.chat as chat_model
import models.profile_extras as extras
from models.user import find_by_id
from utils.security import decode_token
from utils.serializers import chat_message_public, chat_user_public

logger = logging.getLogger("portfolio.sockets")

# threading async_mode needs no extra dependency (no eventlet/gevent) —
# fine for a single dev/small-deployment process. cors_allowed_origins
# mirrors app.py's CORS() setup so the Socket.IO handshake isn't blocked
# by the browser separately from the REST API.
socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")

# sid -> user_id, and the reverse index, so disconnect can look up who
# left without the client having to tell us again.
_sid_to_user = {}
_user_sids = {}  # user_id -> set of sids (same user, multiple tabs)


def _authenticate(auth=None):
    """Accepts the token from wherever the client put it: the Socket.IO
    `auth` payload (what assets/js/chat.js sends), a `?token=` query
    param, or an Authorization header — in that order."""
    token = None
    if auth and isinstance(auth, dict) and auth.get("token"):
        token = auth["token"]
    elif request.args.get("token"):
        token = request.args.get("token")
    else:
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            token = header.split(" ", 1)[1].strip()

    if not token:
        return None
    try:
        payload = decode_token(token)
        return payload["sub"]
    except Exception:
        return None


def _broadcast_presence(user_id, is_online):
    """Tell everyone this user has an active conversation with that
    their online status changed — cheaper than a global broadcast and
    keeps the payload meaningful (only people who'd show it in a
    sidebar get it)."""
    conversations = chat_model.list_conversations_for_user(user_id)
    user = find_by_id(user_id)
    if not user:
        return
    payload = {"user": chat_user_public({**user, "is_online": is_online})}
    for conv in conversations:
        other_id = conv["other_user"]["id"]
        for sid in _user_sids.get(other_id, ()):
            emit("presence", payload, room=sid)


@socketio.on("connect")
def handle_connect(auth=None):
    user_id = _authenticate(auth)
    if user_id is None:
        logger.info("Rejected unauthenticated socket connection from %s", request.remote_addr)
        return False  # reject the handshake

    _sid_to_user[request.sid] = user_id
    _user_sids.setdefault(user_id, set()).add(request.sid)

    # A personal room lets this module push "your conversation list
    # changed" events to a user regardless of which conversation room
    # they currently have open.
    join_room(f"user:{user_id}")

    was_offline = len(_user_sids[user_id]) == 1
    if was_offline:
        chat_model.set_online_status(user_id, True)
        _broadcast_presence(user_id, True)


@socketio.on("disconnect")
def handle_disconnect():
    user_id = _sid_to_user.pop(request.sid, None)
    if user_id is None:
        return

    sids = _user_sids.get(user_id)
    if sids:
        sids.discard(request.sid)
        if not sids:
            del _user_sids[user_id]
            chat_model.set_online_status(user_id, False)
            _broadcast_presence(user_id, False)


@socketio.on("join_conversation")
def handle_join_conversation(data):
    user_id = _sid_to_user.get(request.sid)
    conversation_id = (data or {}).get("conversation_id")
    if not user_id or not conversation_id:
        return
    if not chat_model.is_participant(conversation_id, user_id):
        return  # silently ignore — not your conversation
    join_room(f"conv:{conversation_id}")


@socketio.on("leave_conversation")
def handle_leave_conversation(data):
    conversation_id = (data or {}).get("conversation_id")
    if conversation_id:
        leave_room(f"conv:{conversation_id}")


@socketio.on("typing")
def handle_typing(data):
    user_id = _sid_to_user.get(request.sid)
    conversation_id = (data or {}).get("conversation_id")
    is_typing = bool((data or {}).get("is_typing"))
    if not user_id or not conversation_id:
        return
    if not chat_model.is_participant(conversation_id, user_id):
        return

    emit(
        "typing",
        {"conversation_id": conversation_id, "user_id": user_id, "is_typing": is_typing},
        room=f"conv:{conversation_id}",
        include_self=False,
    )


@socketio.on("send_message")
def handle_send_message(data):
    user_id = _sid_to_user.get(request.sid)
    if not user_id:
        return emit("error", {"error": "Not authenticated."})

    data = data or {}
    conversation_id = data.get("conversation_id")
    message_type = data.get("message_type", "text")
    body = (data.get("body") or "").strip() or None
    attachment_url = data.get("attachment_url")
    attachment_name = data.get("attachment_name")

    if not conversation_id or not chat_model.is_participant(conversation_id, user_id):
        return emit("error", {"error": "Conversation not found."})

    if message_type == "text" and not body:
        return emit("error", {"error": "Message can't be empty."})
    if message_type in ("image", "document") and not attachment_url:
        return emit("error", {"error": "Missing attachment."})
    if body and len(body) > 4000:
        return emit("error", {"error": "Message is too long (max 4000 characters)."})

    message = chat_model.create_message(
        conversation_id, user_id, message_type, body, attachment_url, attachment_name
    )
    payload = chat_message_public(message)

    # Everyone actively viewing the conversation gets the message instantly...
    emit("new_message", payload, room=f"conv:{conversation_id}")

    # ...and both participants' sidebars (which may not have the
    # conversation room joined right now) get told to refresh their
    # preview/unread badge.
    other = chat_model.get_other_participant(conversation_id, user_id)
    if other:
        emit(
            "conversation_update",
            {"conversation_id": conversation_id, "last_message": payload},
            room=f"user:{other['id']}",
        )
        # They're not connected at all right now (not just "not viewing
        # this conversation") — leave them a Notification Center entry
        # so they see it was missed next time they sign in, same idea as
        # an email/push notification would give elsewhere.
        if other["id"] not in _user_sids:
            recipient = find_by_id(other["id"])
            if recipient and recipient.get("notify_chat", True):
                sender = find_by_id(user_id)
                sender_name = sender["name"] if sender else "Someone"
                preview = body[:80] if body else ("Sent an attachment" if message_type != "text" else "")
                extras.create_notification(
                    other["id"], "chat", f"New message from {sender_name}",
                    preview, link="/chat.html",
                )


@socketio.on("mark_read")
def handle_mark_read(data):
    user_id = _sid_to_user.get(request.sid)
    data = data or {}
    conversation_id = data.get("conversation_id")
    message_id = data.get("message_id")

    if not user_id or not conversation_id or not message_id:
        return
    if not chat_model.is_participant(conversation_id, user_id):
        return

    chat_model.mark_read(conversation_id, user_id, message_id)
    emit(
        "read_receipt",
        {"conversation_id": conversation_id, "user_id": user_id, "message_id": message_id},
        room=f"conv:{conversation_id}",
        include_self=False,
    )


@socketio.on("delete_message")
def handle_delete_message(data):
    """Mirrors DELETE /api/chat/messages/<id> (routes/chat.py) but also
    broadcasts the deletion live, so the other participant sees "This
    message was deleted" immediately instead of on their next refresh.
    Only the sender can delete their own message — soft_delete_message
    already enforces that at the DB layer, this just checks first so we
    don't broadcast anything on a rejected attempt."""
    user_id = _sid_to_user.get(request.sid)
    data = data or {}
    message_id = data.get("message_id")
    if not user_id or not message_id:
        return

    message = chat_model.get_message(message_id)
    if not message or message["sender_id"] != user_id:
        return

    deleted = chat_model.soft_delete_message(message_id, user_id)
    if not deleted:
        return

    emit(
        "message_deleted",
        {"conversation_id": message["conversation_id"], "message_id": message_id},
        room=f"conv:{message['conversation_id']}",
    )
