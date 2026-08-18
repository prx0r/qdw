-- RouteLLM model pairs
CREATE TABLE IF NOT EXISTS route_llm_pairs (
    pair_id TEXT PRIMARY KEY,
    strong_model TEXT NOT NULL,
    weak_model TEXT NOT NULL,
    strategy TEXT NOT NULL,
    created_at TEXT NOT NULL
);
