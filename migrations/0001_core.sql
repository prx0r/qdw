-- QDW core schema — numbered migration 0001
-- Tables: ledger, work graph, factories, verification, economics, scheduling, global infrastructure

PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS schema_versions (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ledger_events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    occurred_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    prev_event_hash TEXT,
    event_hash TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ledger_epochs (
    epoch_id TEXT PRIMARY KEY,
    start_seq INTEGER NOT NULL,
    end_seq INTEGER NOT NULL,
    leaf_count INTEGER NOT NULL,
    merkle_root TEXT NOT NULL,
    created_at TEXT NOT NULL,
    signature_b64 TEXT,
    signer_key_id TEXT,
    external_anchor_json TEXT
);

CREATE TABLE IF NOT EXISTS work_graphs (
    graph_id TEXT PRIMARY KEY,
    factory_run_id TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    graph_hash TEXT
);

CREATE TABLE IF NOT EXISTS work_nodes (
    node_id TEXT PRIMARY KEY,
    graph_id TEXT NOT NULL REFERENCES work_graphs(graph_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    state TEXT NOT NULL,
    priority REAL NOT NULL DEFAULT 0,
    expected_value REAL,
    expected_cost REAL,
    quality_floor REAL,
    max_retries INTEGER NOT NULL DEFAULT 2,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    lease_owner TEXT,
    lease_until TEXT,
    idempotency_key TEXT UNIQUE,
    payload_json TEXT NOT NULL,
    result_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS work_edges (
    graph_id TEXT NOT NULL REFERENCES work_graphs(graph_id) ON DELETE CASCADE,
    from_node TEXT NOT NULL REFERENCES work_nodes(node_id) ON DELETE CASCADE,
    to_node TEXT NOT NULL REFERENCES work_nodes(node_id) ON DELETE CASCADE,
    relation TEXT NOT NULL DEFAULT 'blocks',
    PRIMARY KEY(graph_id, from_node, to_node, relation)
);

CREATE INDEX IF NOT EXISTS idx_nodes_state ON work_nodes(state, priority DESC);
CREATE INDEX IF NOT EXISTS idx_edges_to ON work_edges(to_node);

CREATE TABLE IF NOT EXISTS factory_definitions (
    factory_id TEXT NOT NULL,
    version TEXT NOT NULL,
    definition_hash TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'CANDIDATE',
    created_at TEXT NOT NULL,
    PRIMARY KEY(factory_id, version)
);

CREATE TABLE IF NOT EXISTS factory_runs (
    factory_run_id TEXT PRIMARY KEY,
    factory_id TEXT NOT NULL,
    factory_version TEXT NOT NULL,
    opportunity_id TEXT,
    graph_id TEXT,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    decision_snapshot_hash TEXT,
    total_cost_usd REAL NOT NULL DEFAULT 0,
    certificate_id TEXT
);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    factory_run_id TEXT,
    node_id TEXT,
    sha256 TEXT NOT NULL,
    media_type TEXT,
    size_bytes INTEGER,
    uri TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(factory_run_id, sha256)
);

CREATE TABLE IF NOT EXISTS gate_results (
    gate_result_id TEXT PRIMARY KEY,
    factory_run_id TEXT,
    node_id TEXT,
    gate_id TEXT NOT NULL,
    passed INTEGER NOT NULL,
    result_hash TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS certificates (
    certificate_id TEXT PRIMARY KEY,
    factory_run_id TEXT NOT NULL UNIQUE,
    attestation_json TEXT NOT NULL,
    attestation_hash TEXT NOT NULL,
    issued_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cost_events (
    cost_event_id TEXT PRIMARY KEY,
    factory_run_id TEXT,
    node_id TEXT,
    category TEXT NOT NULL,
    provider TEXT,
    amount_usd REAL NOT NULL,
    quantity REAL,
    unit TEXT,
    occurred_at TEXT NOT NULL,
    evidence_ref TEXT
);

CREATE TABLE IF NOT EXISTS releases (
    release_id TEXT PRIMARY KEY,
    factory_run_id TEXT NOT NULL,
    target TEXT NOT NULL,
    external_ref TEXT,
    released_at TEXT NOT NULL,
    release_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outcomes (
    outcome_id TEXT PRIMARY KEY,
    release_id TEXT NOT NULL REFERENCES releases(release_id),
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    metrics_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    schedule_id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    trigger_kind TEXT NOT NULL,
    trigger_json TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    budget_usd REAL,
    concurrency_cap INTEGER NOT NULL DEFAULT 1,
    enabled INTEGER NOT NULL DEFAULT 1,
    last_enqueued_at TEXT,
    next_eligible_at TEXT,
    idempotency_template TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS factory_stats (
    factory_id TEXT NOT NULL,
    factory_version TEXT NOT NULL,
    runs INTEGER NOT NULL DEFAULT 0,
    certified_runs INTEGER NOT NULL DEFAULT 0,
    success_alpha REAL NOT NULL DEFAULT 1,
    success_beta REAL NOT NULL DEFAULT 1,
    total_cost_usd REAL NOT NULL DEFAULT 0,
    total_utility REAL NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(factory_id, factory_version)
);
