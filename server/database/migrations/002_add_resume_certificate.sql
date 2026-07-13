-- Run this once against your EXISTING database if you already created it
-- before this change:
--   mysql -u root -p shubham_portfolio < server/database/migrations/002_add_resume_certificate.sql
--
-- (If you're setting up the database for the first time, skip this —
--  the updated server/database/schema.sql already includes these columns.)

USE shubham_portfolio;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS resume      VARCHAR(255) NULL AFTER bio,
  ADD COLUMN IF NOT EXISTS certificate VARCHAR(255) NULL AFTER resume;
