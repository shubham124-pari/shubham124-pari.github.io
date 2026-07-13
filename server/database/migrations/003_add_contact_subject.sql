-- Run this once against your EXISTING database:
--   mysql -u root -p shubham_portfolio < server/database/migrations/003_add_contact_subject.sql
--
-- (Fresh installs: skip this — schema.sql already includes this column.)

USE shubham_portfolio;

ALTER TABLE contact_messages
  ADD COLUMN IF NOT EXISTS subject VARCHAR(200) NULL AFTER email;
