CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    r2_key VARCHAR(512) NOT NULL,
    content_type VARCHAR(255) DEFAULT 'application/octet-stream',
    size BIGINT DEFAULT 0,
    download_url TEXT NOT NULL,
    access_key VARCHAR(6) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_files_access_key ON files(access_key);
CREATE INDEX IF NOT EXISTS idx_files_expires_at ON files(expires_at);

CREATE TABLE IF NOT EXISTS stats (
    id SERIAL PRIMARY KEY,
    total_uploads BIGINT DEFAULT 0,
    total_downloads BIGINT DEFAULT 0,
    total_upload_bytes BIGINT DEFAULT 0,
    total_download_bytes BIGINT DEFAULT 0
);

-- Seed a single row if empty
INSERT INTO stats (id, total_uploads, total_downloads, total_upload_bytes, total_download_bytes)
VALUES (1, 0, 0, 0, 0)
ON CONFLICT (id) DO NOTHING;
