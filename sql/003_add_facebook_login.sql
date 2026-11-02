ALTER TABLE users
    ADD COLUMN IF NOT EXISTS facebook_id VARCHAR(255) UNIQUE;

CREATE INDEX IF NOT EXISTS users_facebook_id_idx ON users (facebook_id);
