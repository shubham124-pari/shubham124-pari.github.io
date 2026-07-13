-- Run this once against your EXISTING database:
--   mysql -u root -p shubham_portfolio < server/database/migrations/005_add_chat_and_presence.sql
--
-- (Fresh installs: skip this — schema.sql already includes all of this.)
--
-- Adds: private one-to-one chat (conversations/messages), typing/online
-- presence columns on users, and per-participant read-receipt tracking.

USE shubham_portfolio;

-- Online-status + "last seen" for presence indicators in the chat UI.
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS is_online TINYINT(1)  NOT NULL DEFAULT 0 AFTER is_banned,
  ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP   NULL             AFTER is_online;

-- A conversation is currently always type='direct' (one-to-one). The
-- 'type' column exists so group chat can be added later without a
-- schema change.
CREATE TABLE IF NOT EXISTS conversations (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    type       VARCHAR(20) NOT NULL DEFAULT 'direct',
    created_at TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Who is in each conversation. last_read_message_id drives read receipts:
-- a message is "seen" by a participant once their last_read_message_id
-- is >= that message's id.
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

-- message_type: 'text' | 'image' | 'document'. attachment_url/name are
-- only set for image/document messages (uploaded via
-- POST /api/user/upload/chat_image or /upload/chat_document).
-- deleted_at is a soft delete: the row stays (so message ids and
-- conversation ordering stay stable) but the body/attachment are
-- blanked out and the UI shows "This message was deleted".
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
