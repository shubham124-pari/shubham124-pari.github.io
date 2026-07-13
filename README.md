# Shubham Kumar — Portfolio (shubham124-pari.github.io)

A personal, cybersecurity-focused developer portfolio: static frontend
(GitHub Pages) + a Flask/MySQL backend (`server/`) with real accounts,
a projects/resume/certificate dashboard, an admin panel, a cybersecurity
toolkit, private one-to-one chat, and a multilingual AI assistant.

## Highlights

- **Auth** — signup/login, JWT sessions, forgot/reset password
- **User Dashboard** — profile, cover + profile picture, bio, skills,
  education, experience, project CRUD, resume/certificate upload &
  replace, notification center, activity timeline, theme/privacy/
  notification settings, change password, delete account, personal
  dashboard analytics (see below)
- **Admin panel** — user management, contact inbox, analytics
- **Cybersecurity toolkit** — password generator, hash generator (more planned)
- **Private Chat** — real-time one-to-one messaging (see below)
- **Social Features** — public `/u/<username>` profiles, follows,
  connections (accept/reject), posts (text/image/video), likes, comments,
  shares, bookmarks, and a personalized feed (see `server/docs/SOCIAL_FEATURES.md`)
- **AI Assistant** — multilingual, domain-aware chatbot (see below)
- **Security** — hashed passwords, parameterized SQL, rate limiting, CORS,
  security headers, upload validation (real-image checks + EXIF stripping)

## User Dashboard

Everything a signed-in member manages about their own account lives at
**`/dashboard.html`**, in a glassmorphism UI with 10 tabs:

| Tab | What's there |
|---|---|
| Overview | Cover + profile photo header, dashboard analytics (project/skill/chat/AI-conversation counts, unread notifications), profile-completeness check |
| Profile | Name, bio |
| Skills | Add/edit/delete skills with a 1–5 level |
| Background | Education timeline + work experience timeline, both full CRUD |
| Projects | Existing project CRUD (title, description, links, image) |
| Uploads | Profile photo, cover photo, resume (PDF), certificate |
| Notifications | Notification Center — chat/account notifications, mark read / mark all read |
| Activity | Activity timeline — logins, profile edits, uploads, project changes, settings changes |
| Support | Contact/bug-report form + your message history |
| Settings | Theme (dark/light), privacy (public/private profile), notification preferences, change password, delete account |

Backed by `server/routes/user.py` + `server/models/profile_extras.py` +
migration `006_add_dashboard_extras.sql` (`user_skills`,
`user_education`, `user_experience`, `notifications`, `activity_log`
tables, plus `cover_photo`/`theme`/`profile_visibility`/`notify_*`
columns on `users`). Notifications are also created automatically —
e.g. a chat message notification lands in the Notification Center for a
recipient who's fully offline (`server/sockets.py`) — and key actions
(login, profile edit, password change, uploads, project changes,
settings changes) are recorded to the activity timeline.

## Private Chat

Sign-in members can message each other in real time from **`/chat.html`**.

| Feature | How |
|---|---|
| One-to-one messaging | `server/models/chat.py` + `server/routes/chat.py` |
| Typing indicator | Socket.IO `typing` event (`server/sockets.py`) |
| Online status | `users.is_online` / `last_seen`, broadcast via `presence` event |
| Read receipts | `conversation_participants.last_read_message_id` + `read_receipt` event |
| Image sharing | `POST /api/user/upload/chat_image` → attach URL to a message |
| Document sharing | `POST /api/user/upload/chat_document` (pdf/doc/docx/txt/zip) |
| Conversation history | `GET /api/chat/conversations/<id>/messages` (paginated) |
| Search messages | `GET /api/chat/search?q=` (across all your conversations) |
| Delete messages | `DELETE /api/chat/messages/<id>` (soft delete, own messages only) |
| Notifications | `conversation_update` event bumps the sidebar/unread badge live |

The REST endpoints (`routes/chat.py`) cover page-load data; everything
that needs to be *pushed* live (new messages, typing, presence, read
receipts, live deletion) goes over Socket.IO (`sockets.py`), authenticated
with the same JWT the REST API uses — no separate chat login.

## AI Assistant

The floating chat widget (every page) and `/api/chatbot/ask` are powered by
`server/services/ai_provider.py`:

- **Auto language detection** — `server/services/language.py` (via
  `langdetect`) detects the visitor's language and the assistant replies
  in that same language, whatever it is.
- **Five question domains** — programming, cybersecurity, career advice,
  resume help, and questions about Shubham's own portfolio (grounded in
  real project data pulled live from the database).
- **Conversation memory** — the last 6 exchanges are sent back on every
  call, so follow-up questions work. Signed-in users' history is kept
  server-side (`chatbot_history` table, tied to their account); signed-out
  visitors' history lives in the browser tab for that session.
- **Markdown + code highlighting** — answers are rendered with `marked.js`
  and `highlight.js`, so code blocks come back properly formatted.
- Works with **either Gemini or OpenAI** — set `AI_PROVIDER=gemini|openai`
  in `server/.env`. Both are called over plain HTTPS (`urllib`, stdlib
  only), so no provider SDK is required.

## Tech stack

- **Backend**: Flask, Flask-SocketIO, PyMySQL, PyJWT, Pillow, langdetect
- **Frontend**: static HTML/CSS/JS (no build step), Socket.IO client,
  marked.js, highlight.js — all via CDN
- **Database**: MySQL
- **Testing**: pytest (mocked at the model layer — no live DB required to run the suite)

## Project structure

```
shubham124-pari.github.io/
├── index.html, about.html, skills.html, projects.html, ...   # public pages
├── dashboard.html                  # signed-in member dashboard
├── admin.html                      # admin panel
├── chat.html                       # private chat
├── toolkit.html                    # cybersecurity toolkit
├── assets/
│   ├── css/style.css
│   ├── js/
│   │   ├── auth.js                 # session/auth helpers used by every page
│   │   ├── script.js                # page transitions, misc UI
│   │   ├── matrix.js                # background effect
│   │   ├── dashboard.js, admin.js, toolkit.js
│   │   ├── chat.js                  # private chat (Socket.IO client)
│   │   └── chatbot.js               # floating AI assistant widget
│   ├── images/, fonts/, documents/
└── server/                          # Flask + MySQL backend
    ├── app.py                       # app factory, blueprints, Socket.IO attach
    ├── sockets.py                   # real-time chat: presence, typing, messages, read receipts
    ├── config.py
    ├── requirements.txt
    ├── SETUP.md
    ├── database/
    │   ├── schema.sql                # fresh-install schema (all tables)
    │   └── migrations/               # 002–006, for existing installs
    ├── models/                       # raw parameterized-SQL data access
    │   ├── user.py, project.py, contact.py, chatbot.py, admin.py
    │   ├── chat.py                   # conversations / messages / presence / read receipts
    │   └── profile_extras.py         # skills / education / experience / notifications / activity log
    ├── routes/                       # Flask blueprints
    │   ├── auth.py, user.py, upload.py, project.py, contact.py, admin.py
    │   ├── chatbot.py                # multilingual AI assistant endpoint
    │   └── chat.py                   # private chat REST endpoints
    ├── services/
    │   ├── ai_provider.py            # Gemini/OpenAI, multilingual, domain-aware
    │   └── language.py               # language detection
    ├── utils/
    │   ├── security.py               # password hashing, JWT
    │   ├── serializers.py            # response shaping (never leak password hashes, etc.)
    │   └── email.py
    └── tests/                        # pytest suite (mocked model layer)
        ├── conftest.py
        ├── test_auth.py, test_security.py
        ├── test_chat.py              # chat REST endpoints
        ├── test_ai_assistant.py      # language detection + provider routing
        └── test_dashboard_extras.py  # skills / education / experience / settings / notifications / activity
```

## Getting started

See **`server/SETUP.md`** for the full step-by-step (database, `.env`,
running the server, creating your admin account). Short version:

```bash
mysql -u root -p < server/database/schema.sql   # fresh install
cd server
pip install -r requirements.txt
python app.py                                    # runs on http://127.0.0.1:5000
```

Then open the frontend through a local server (not `file://` — see
`server/SETUP.md` for why), e.g. `python -m http.server 5500`.

### Running tests

```bash
cd server
pytest
```

## Environment variables

All configuration lives in `server/.env` (see `server/config.py` for the
full list). The additions for this phase:

```
# AI Assistant (existing — now multilingual + domain-aware automatically)
AI_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
```

No new environment variables were needed for Private Chat — it reuses the
same JWT/session setup as the rest of the site.
