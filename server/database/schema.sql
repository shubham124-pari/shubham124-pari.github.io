-- Run this once against your MySQL server to create the database & tables:
--   mysql -u root -p < server/database/schema.sql

CREATE DATABASE IF NOT EXISTS shubham_portfolio
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE shubham_portfolio;

-- Used starting Phase 1 (auth)
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(120)  NOT NULL,
    username      VARCHAR(30)   NULL UNIQUE,   -- used to build /u/<username> profile URLs
    email         VARCHAR(190)  NOT NULL UNIQUE,
    password      VARCHAR(255)  NOT NULL,   -- hashed, never plain text
    profile_photo VARCHAR(255)  NULL,
    cover_photo   VARCHAR(255)  NULL,
    bio           TEXT          NULL,
    resume        VARCHAR(255)  NULL,
    certificate   VARCHAR(255)  NULL,
    role          VARCHAR(20)   NOT NULL DEFAULT 'user',   -- 'user' | 'admin'
    theme              VARCHAR(20) NOT NULL DEFAULT 'dark',
    profile_visibility VARCHAR(20) NOT NULL DEFAULT 'public',
    notify_email       TINYINT(1)  NOT NULL DEFAULT 1,
    notify_chat        TINYINT(1)  NOT NULL DEFAULT 1,
    is_banned     TINYINT(1)    NOT NULL DEFAULT 0,
    is_online     TINYINT(1)    NOT NULL DEFAULT 0,
    last_seen     TIMESTAMP     NULL,
    reset_token        VARCHAR(255)  NULL,
    reset_token_expiry TIMESTAMP     NULL,
    created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Used starting a later phase (dashboard: projects)
CREATE TABLE IF NOT EXISTS projects (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    title       VARCHAR(150) NOT NULL,
    description TEXT NULL,
    image       VARCHAR(255) NULL,
    github      VARCHAR(255) NULL,
    demo        VARCHAR(255) NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Used starting the AI chatbot phase
-- user_id is nullable: the chatbot widget also works for signed-out
-- visitors, so not every row belongs to a registered user.
CREATE TABLE IF NOT EXISTS chatbot_history (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NULL,
    question   TEXT NOT NULL,
    answer     TEXT NOT NULL,
    time       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Used starting the contact-form phase
-- user_id is nullable: anonymous visitors can use the public contact
-- form; logged-in users submitting from the dashboard get linked so
-- they can see their own message history.
CREATE TABLE IF NOT EXISTS contact_messages (
    id      INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    name    VARCHAR(120) NOT NULL,
    email   VARCHAR(190) NOT NULL,
    subject VARCHAR(200) NULL,
    message TEXT NOT NULL,
    status  VARCHAR(20) NOT NULL DEFAULT 'new',   -- 'new' | 'read' | 'resolved'
    date    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Used starting the private chat phase (one-to-one messaging).
-- 'type' is always 'direct' today; kept so group chat can be added later
-- without a schema change.
CREATE TABLE IF NOT EXISTS conversations (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    type       VARCHAR(20) NOT NULL DEFAULT 'direct',
    created_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- last_read_message_id drives read receipts: a message is "seen" by a
-- participant once their last_read_message_id is >= that message's id.
CREATE TABLE IF NOT EXISTS conversation_participants (
    id                    INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id       INT NOT NULL,
    user_id               INT NOT NULL,
    last_read_message_id  INT NULL,
    joined_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_conversation_user (conversation_id, user_id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- message_type: 'text' | 'image' | 'document'. deleted_at is a soft
-- delete — the row stays (keeps ordering/ids stable) but the UI shows
-- "This message was deleted" once it's set.
CREATE TABLE IF NOT EXISTS messages (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    conversation_id INT NOT NULL,
    sender_id       INT NOT NULL,
    message_type    VARCHAR(20) NOT NULL DEFAULT 'text',
    body            TEXT NULL,
    attachment_url  VARCHAR(255) NULL,
    attachment_name VARCHAR(255) NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at      TIMESTAMP NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_messages_conversation (conversation_id, created_at),
    FULLTEXT INDEX idx_messages_body (body)
);

-- Used starting the expanded dashboard phase.
CREATE TABLE IF NOT EXISTS user_skills (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    name       VARCHAR(80) NOT NULL,
    level      TINYINT NOT NULL DEFAULT 3,   -- 1-5
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_education (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    school      VARCHAR(150) NOT NULL,
    degree      VARCHAR(150) NULL,
    field       VARCHAR(150) NULL,
    start_year  SMALLINT NULL,
    end_year    SMALLINT NULL,
    description TEXT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_experience (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    company     VARCHAR(150) NOT NULL,
    role        VARCHAR(150) NOT NULL,
    start_date  DATE NULL,
    end_date    DATE NULL,
    is_current  TINYINT(1) NOT NULL DEFAULT 0,
    description TEXT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    type       VARCHAR(40) NOT NULL DEFAULT 'system',
    title      VARCHAR(200) NOT NULL,
    body       VARCHAR(500) NULL,
    link       VARCHAR(255) NULL,
    is_read    TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_notifications_user (user_id, created_at)
);

CREATE TABLE IF NOT EXISTS activity_log (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    action     VARCHAR(80) NOT NULL,
    meta       VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_activity_user (user_id, created_at)
);

-- ---------------------------------------------------
-- Social features: follows, connections, posts + interactions.
-- See server/docs/SOCIAL_FEATURES.md for the full design writeup.
-- ---------------------------------------------------

-- One-directional follow, no approval needed.
CREATE TABLE IF NOT EXISTS follows (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    follower_id  INT NOT NULL,
    followee_id  INT NOT NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_follow (follower_id, followee_id),
    FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (followee_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_no_self_follow CHECK (follower_id <> followee_id)
);

-- Two-directional connection, requires accept.
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

CREATE INDEX idx_posts_user_created ON posts (user_id, created_at DESC);
CREATE INDEX idx_follows_followee ON follows (followee_id);
CREATE INDEX idx_connection_addressee_status ON connection_requests (addressee_id, status);
