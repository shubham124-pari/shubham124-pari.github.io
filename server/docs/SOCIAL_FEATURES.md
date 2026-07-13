# Social Networking Features

This phase adds a social layer on top of the existing accounts system:
public/private profiles, a follow system, connection requests, a news
feed, posts (text/image/video), and the usual interactions (like,
comment, share, bookmark).

## 1. Data model

New tables (see `database/schema.sql` for fresh installs, or run
`database/migrations/005_add_social_features.sql` against an existing
database):

| Table                 | Purpose                                              |
|-----------------------|-------------------------------------------------------|
| `users` (altered)     | + `username` (unique, used in profile URLs), + `profile_visibility` |
| `follows`             | one-directional, no approval needed                   |
| `connection_requests` | two-directional, requires accept (pending/accepted/rejected) |
| `posts`               | text / image / video, each with its own `visibility`  |
| `post_likes`          | one row per (post, user)                              |
| `post_comments`       | flat comments, no threading                           |
| `post_shares`         | one row per (post, user), optional note                |
| `post_bookmarks`      | always private to the bookmarking user                |

## 2. Privacy model — the important part

Three visibility levels exist on **both** the profile and each individual
post: `public`, `connections_only`, `private`.

- **Profile-level** (`users.profile_visibility`) gates the profile page
  itself, and the followers/following lists, and — critically — whether
  someone can see the user's uploaded files (resume/certificate/photo)
  and post list at all.
- **Post-level** (`posts.visibility`) gates that individual post,
  independent of the author's overall profile setting. A public-profile
  account can still post something `private`.

**Every** route that returns another user's profile or posts routes its
decision through exactly one place: `utils/privacy.py`
(`can_view_profile`, `can_view_post`, `can_view_files`). This is
deliberate — it's what makes "a user must never see another user's
private files" a single, auditable rule instead of a check that has to
be remembered in a dozen different route handlers. Both functions
**fail closed**: any visibility value they don't recognize is treated as
"can't view."

Interaction routes (`like`, `comment`, `share`, `bookmark`) all call the
same `can_view_post` check *before* acting — this stops someone from
confirming a private post exists (or reading its content indirectly)
just by trying to like/comment on a guessed post ID.

## 3. API summary

All endpoints are JSON, `Authorization: Bearer <token>` where noted.
Endpoints marked "optional auth" work for signed-out visitors too
(they just fall back to the public-only view).

### Profiles
- `GET /api/social/profile/<username>` — optional auth
- `PUT /api/social/profile/settings` — auth. Body: `{username, profile_visibility}`
- `GET /api/social/search?q=` — auth. Name/username search.

### Follow
- `POST /api/social/follow/<user_id>` — auth
- `DELETE /api/social/follow/<user_id>` — auth
- `GET /api/social/followers/<username>` — optional auth
- `GET /api/social/following/<username>` — optional auth

### Connections
- `POST /api/social/connections/request/<user_id>` — auth
- `POST /api/social/connections/<request_id>/accept` — auth (addressee only)
- `POST /api/social/connections/<request_id>/reject` — auth (addressee only)
- `GET /api/social/connections/pending` — auth
- `GET /api/social/connections` — auth

### Posts
- `POST /api/posts` — auth. Body: `{post_type, content, media_url, visibility}`
- `PUT /api/posts/<id>` — auth, author only
- `DELETE /api/posts/<id>` — auth, author only
- `GET /api/posts/<id>` — optional auth, gated by `can_view_post`
- `GET /api/posts/user/<username>` — optional auth, gated by `can_view_profile` + `can_view_post`
- `GET /api/posts/feed` — auth. Posts from people you follow/are connected with, plus your own.
- `GET /api/posts/explore` — optional auth. Public posts only.

### Media upload (reuses the existing `/api/user/upload/<kind>` endpoint)
- `POST /api/user/upload/post_image` — jpg/jpeg/png, 5MB, resized to 1600px
- `POST /api/user/upload/post_video` — mp4/webm/mov, 10MB, stored as-is (no server-side transcoding)

Both return `{"image": "/uploads/posts/<file>"}` — pass that URL as
`media_url` when creating the post.

### Interactions
- `POST/DELETE /api/posts/<id>/like` — auth
- `POST /api/posts/<id>/comments`, `GET /api/posts/<id>/comments` — comment auth, read optional auth
- `DELETE /api/posts/comments/<comment_id>` — auth, comment author only
- `POST /api/posts/<id>/share` — auth
- `POST/DELETE /api/posts/<id>/bookmark` — auth
- `GET /api/posts/bookmarks` — auth, always scoped to the caller

## 4. Frontend

- `feed.html` + `assets/js/feed.js` — signed-in news feed, create/edit/delete
  post, like/comment/share/bookmark.
- `profile.html` + `assets/js/profile.js` — public profile page at
  `profile.html?u=<username>`, follow/connect buttons, post grid, privacy
  settings panel when viewing your own profile.

## 5. Testing

- `tests/test_privacy.py` — pure unit tests of `can_view_profile` /
  `can_view_post` covering all three visibility levels, owner override,
  and the fail-closed default.
- `tests/test_social.py` — route-level tests (profile privacy gate,
  follow/connection ownership rules, post CRUD ownership, and the
  "can't probe a hidden post via like/comment" guard).

Run with `pytest` from `server/` — no live database required, same as
the existing suite (model calls are mocked).

## 6. What's intentionally out of scope for this pass

- Real-time feed updates (websockets) — the feed is pull/refresh based.
- Video transcoding/thumbnailing — videos are stored as uploaded.
- Notifications (new follower, new comment, etc.) — no `notifications` table yet.
- Threaded/nested comments — comments are flat.
- Blocking/muting a user.
