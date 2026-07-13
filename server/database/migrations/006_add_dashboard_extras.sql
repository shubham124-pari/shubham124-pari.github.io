-- Run this once against your EXISTING database:
--   mysql -u root -p shubham_portfolio < server/database/migrations/006_add_dashboard_extras.sql
--
-- (Fresh installs: skip this — schema.sql already includes all of this.)
--
-- Adds everything the expanded User Dashboard needs beyond what already
-- existed (profile/bio, resume, certificate, projects, password change,
-- delete account): cover picture, theme/privacy/notification settings,
-- skills, education, experience, a notification center, and an activity
-- timeline.

USE shubham_portfolio;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS cover_photo        VARCHAR(255) NULL             AFTER profile_photo,
  ADD COLUMN IF NOT EXISTS theme              VARCHAR(20)  NOT NULL DEFAULT 'dark'   AFTER role,
  ADD COLUMN IF NOT EXISTS profile_visibility VARCHAR(20)  NOT NULL DEFAULT 'public' AFTER theme,
  ADD COLUMN IF NOT EXISTS notify_email       TINYINT(1)   NOT NULL DEFAULT 1        AFTER profile_visibility,
  ADD COLUMN IF NOT EXISTS notify_chat        TINYINT(1)   NOT NULL DEFAULT 1        AFTER notify_email;

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
    end_year    SMALLINT NULL,               -- NULL = ongoing
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
    end_date    DATE NULL,                   -- NULL + is_current=1 = "Present"
    is_current  TINYINT(1) NOT NULL DEFAULT 0,
    description TEXT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- type: 'chat' | 'contact' | 'account' | 'system' — drives the icon shown
-- in the Notification Center.
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

-- Powers the Activity Timeline — a lightweight, append-only audit trail
-- of what the account did (profile edits, password changes, uploads,
-- project changes, sign-ins). meta is a short human-readable detail,
-- never sensitive data (no passwords/tokens are ever logged here).
CREATE TABLE IF NOT EXISTS activity_log (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    action     VARCHAR(80) NOT NULL,
    meta       VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_activity_user (user_id, created_at)
);
