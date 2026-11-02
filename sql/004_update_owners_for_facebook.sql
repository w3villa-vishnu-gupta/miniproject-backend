-- Add facebook_id and allow nullable phone for owners (OAuth signup)
ALTER TABLE owners
    ADD COLUMN IF NOT EXISTS facebook_id VARCHAR(255) UNIQUE;

ALTER TABLE owners
    ALTER COLUMN phone DROP NOT NULL;

CREATE INDEX IF NOT EXISTS owners_facebook_id_idx ON owners (facebook_id);
