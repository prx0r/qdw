-- QDW migration 0003: HotSwap persistent state

CREATE TABLE IF NOT EXISTS route_posteriors (
    cell_id TEXT NOT NULL,
    route_id TEXT NOT NULL,
    alpha REAL NOT NULL DEFAULT 1.0,
    beta REAL NOT NULL DEFAULT 1.0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(cell_id, route_id)
);

CREATE TABLE IF NOT EXISTS route_definitions (
    route_id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    free INTEGER NOT NULL DEFAULT 0,
    input_per_m REAL,
    output_per_m REAL,
    context_tokens INTEGER,
    tools_supported INTEGER,
    json_supported INTEGER,
    reliability REAL,
    latency_ms REAL,
    cheapest_paid_replacement_cost REAL DEFAULT 0.001,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
