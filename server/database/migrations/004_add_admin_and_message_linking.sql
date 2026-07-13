-- Run this once against your EXISTING database:
--   mysql -u root -p shubham_portfolio < server/database/migrations/004_add_admin_and_message_linking.sql
--
-- (Fresh installs: skip this — schema.sql already includes these columns.)

USE shubham_portfolio;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS role      VARCHAR(20) NOT NULL DEFAULT 'user' AFTER certificate,
  ADD COLUMN IF NOT EXISTS is_banned TINYINT(1)  NOT NULL DEFAULT 0      AFTER role,
  ADD COLUMN IF NOT EXISTS reset_token        VARCHAR(255) NULL AFTER is_banned,
  ADD COLUMN IF NOT EXISTS reset_token_expiry TIMESTAMP    NULL AFTER reset_token;

ALTER TABLE contact_messages
  ADD COLUMN IF NOT EXISTS user_id INT NULL AFTER id,
  ADD COLUMN IF NOT EXISTS status  VARCHAR(20) NOT NULL DEFAULT 'new' AFTER message,
  ADD CONSTRAINT fk_contact_messages_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;

-- chatbot_history.user_id needs to become nullable (anonymous chatbot use).
-- MySQL has no "ADD COLUMN IF NOT EXISTS ... MODIFY" shortcut, so this uses
-- MODIFY directly — safe to re-run since it's idempotent.
ALTER TABLE chatbot_history
  MODIFY COLUMN user_id INT NULL;

-- To make your own account the admin, run (replace the email):
--   UPDATE users SET role = 'admin' WHERE email = 'your@email.com';
