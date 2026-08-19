-- R2-Router model registry
CREATE TABLE IF NOT EXISTS r2_models (
    model_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    max_tokens INTEGER NOT NULL DEFAULT 4000,
    created_at TEXT NOT NULL
);
