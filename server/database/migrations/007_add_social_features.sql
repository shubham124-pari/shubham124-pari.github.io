-- Run this once against your EXISTING database:
--   mysql -u root -p shubham_portfolio < server/database/migrations/007_add_social_features.sql
--
-- (Fresh installs: skip this — schema.sql already includes all of this.)
--
-- Adds the social layer (usernames + profile URLs, follows, connections,
-- posts, likes, comments, shares, bookmarks) on top of whatever this
-- database already has from migrations 002-006. profile_visibility
-- already exists as of 006_add_dashboard_extras.sql, so this migration
-- only adds the `username` column, not profile_visibility again.

USE shubham_portfolio;

-- ---------------------------------------------------
-- Profiles: username, used to build /u/<username> profile URLs.
-- ---------------------------------------------------
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS username VARCHAR(30) NULL UNIQUE AFTER name;

-- ---------------------------------------------------
-- Follows: one-directional, no approval needed (Twitter/Instagram-style).
-- Always allowed regardless of the target's profile_visibility — it's
-- *content* (posts) that gets gated by privacy, not the follow edge
-- itself, mirroring how most real platforms behave.
-- ---------------------------------------------------
CREATE TABLE IF NOT EXISTS follows (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    follower_id  INT NOT NULL,   -- the user doing the following
    followee_id  INT NOT NULL,   -- the user being followed
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_follow (follower_id, followee_id),
    FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (followee_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_no_self_follow CHECK (follower_id <> followee_id)
);

-- ---------------------------------------------------
-- Connections: two-directional, requires accept (LinkedIn/Facebook-style).
-- One row per pair; requester/addressee only swap on the *first* request
-- between two users, status transitions pending -> accepted | rejected.
-- ---------------------------------------------------
CREATE TABLE IF NOT EXISTS connection_requests (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    requester_id   INT NOT NULL,
    addressee_id   INT NOT NULL,
    status         VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending|accepted|rejected
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    responded_at   TIMESTAMP NULL,
    UNIQUE KEY uq_connection_pair (requester_id, addressee_id),
    FOREIGN KEY (requester_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (addressee_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_no_self_connect CHECK (requester_id <> addressee_id)
);

-- ---------------------------------------------------
-- Posts
-- ---------------------------------------------------
CREATE TABLE IF NOT EXISTS posts (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    post_type   VARCHAR(10) NOT NULL DEFAULT 'text',  -- text|image|video
    content     TEXT NULL,
    media_url   VARCHAR(255) NULL,
    visibility  VARCHAR(20) NOT NULL DEFAULT 'public', -- public|connections_only|private
    is_edited   TINYINT(1) NOT NULL DEFAULT 0,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS post_likes (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    post_id    INT NOT NULL,
    user_id    INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_like (post_id, user_id),
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS post_comments (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    post_id    INT NOT NULL,
    user_id    INT NOT NULL,
    content    VARCHAR(1000) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- A "share" is a lightweight repost: a pointer to the original post plus
-- an optional comment, owned by the sharer. Deleting the original cascades
-- (removes shares of it); deleting the sharer's account also cascades.
CREATE TABLE IF NOT EXISTS post_shares (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    post_id      INT NOT NULL,
    user_id      INT NOT NULL,
    comment      VARCHAR(500) NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_share (post_id, user_id),
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS post_bookmarks (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    post_id    INT NOT NULL,
    user_id    INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_bookmark (post_id, user_id),
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_posts_user_created ON posts (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_follows_followee ON follows (followee_id);
CREATE INDEX IF NOT EXISTS idx_connection_addressee_status ON connection_requests (addressee_id, status);

-- Backfill: give every existing account a username derived from their id
-- so UNIQUE holds immediately (users should change this to something real
-- from their dashboard afterwards).
UPDATE users SET username = CONCAT('user', id) WHERE username IS NULL;
