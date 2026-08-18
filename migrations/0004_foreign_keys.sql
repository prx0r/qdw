-- QDW migration 0004: Add foreign keys to global tables
-- SQLite does not support ALTER TABLE ADD CONSTRAINT, so we recreate tables with FKs.

PRAGMA foreign_keys=ON;

-- observations: no FK to source_connectors — observations can reference source_ids
-- not present in source_connectors (test data, manual entries, legacy sources).
CREATE TABLE IF NOT EXISTS observations_new (
    observation_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_item_id TEXT,
    source_family TEXT,
    observed_at TEXT,
    published_at TEXT,
    freshness_until TEXT,
    status TEXT NOT NULL,
    error_code TEXT,
    content_hash TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
INSERT OR IGNORE INTO observations_new SELECT * FROM observations;
DROP TABLE IF EXISTS observations;
ALTER TABLE observations_new RENAME TO observations;
CREATE INDEX IF NOT EXISTS idx_obs_source ON observations(source_id, source_item_id);

-- pain_observations: add FK to observations and pain_clusters
CREATE TABLE IF NOT EXISTS pain_observations_new (
    pain_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL REFERENCES observations(observation_id),
    text TEXT NOT NULL,
    normalized_text TEXT,
    fingerprint TEXT,
    intensity REAL NOT NULL DEFAULT 0.5,
    recurrence_hint REAL NOT NULL DEFAULT 0.5,
    workaround TEXT,
    willingness_to_pay REAL,
    machine_solvable REAL NOT NULL DEFAULT 0.5,
    verifiable REAL NOT NULL DEFAULT 0.5,
    cluster_id TEXT NOT NULL REFERENCES pain_clusters(cluster_id),
    created_at TEXT NOT NULL
);
INSERT OR IGNORE INTO pain_observations_new SELECT * FROM pain_observations;
DROP TABLE IF EXISTS pain_observations;
ALTER TABLE pain_observations_new RENAME TO pain_observations;

-- startup_events: add FK to entities and observations
CREATE TABLE IF NOT EXISTS startup_events_new (
    startup_event_id TEXT PRIMARY KEY,
    company_entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    event_type TEXT NOT NULL,
    event_at TEXT NOT NULL,
    amount_usd REAL,
    stage TEXT,
    attributes_json TEXT,
    observation_id TEXT REFERENCES observations(observation_id),
    created_at TEXT NOT NULL
);
INSERT OR IGNORE INTO startup_events_new SELECT * FROM startup_events;
DROP TABLE IF EXISTS startup_events;
ALTER TABLE startup_events_new RENAME TO startup_events;

-- resource_measurements: add FK to resources and observations
CREATE TABLE IF NOT EXISTS resource_measurements_new (
    measurement_id TEXT PRIMARY KEY,
    resource_id TEXT NOT NULL REFERENCES resources(resource_id),
    metric TEXT NOT NULL,
    value REAL,
    text_value TEXT,
    unit TEXT,
    observed_at TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    observation_id TEXT REFERENCES observations(observation_id),
    created_at TEXT NOT NULL
);
INSERT OR IGNORE INTO resource_measurements_new SELECT * FROM resource_measurements;
DROP TABLE IF EXISTS resource_measurements;
ALTER TABLE resource_measurements_new RENAME TO resource_measurements;

-- resources: add FK to capabilities
CREATE TABLE IF NOT EXISTS resources_new (
    resource_id TEXT PRIMARY KEY,
    capability_id TEXT NOT NULL REFERENCES capabilities(capability_id),
    provider_entity_id TEXT REFERENCES entities(entity_id),
    resource_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    version TEXT,
    interface_kind TEXT,
    attributes_json TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
INSERT OR IGNORE INTO resources_new SELECT * FROM resources;
DROP TABLE IF EXISTS resources;
ALTER TABLE resources_new RENAME TO resources;

-- idea_relations: add FK to ideas
CREATE TABLE IF NOT EXISTS idea_relations_new (
    relation_id TEXT PRIMARY KEY,
    from_idea_id TEXT NOT NULL REFERENCES ideas(idea_id),
    relation_type TEXT NOT NULL,
    to_idea_id TEXT NOT NULL REFERENCES ideas(idea_id),
    rationale TEXT,
    created_at TEXT NOT NULL
);
INSERT OR IGNORE INTO idea_relations_new SELECT * FROM idea_relations;
DROP TABLE IF EXISTS idea_relations;
ALTER TABLE idea_relations_new RENAME TO idea_relations;

-- idea_decisions: add FK to ideas
CREATE TABLE IF NOT EXISTS idea_decisions_new (
    decision_id TEXT PRIMARY KEY,
    idea_id TEXT NOT NULL REFERENCES ideas(idea_id),
    stage TEXT NOT NULL,
    decision TEXT NOT NULL,
    score_json TEXT,
    reason_codes_json TEXT,
    snapshot_hash TEXT,
    created_at TEXT NOT NULL
);
INSERT OR IGNORE INTO idea_decisions_new SELECT * FROM idea_decisions;
DROP TABLE IF EXISTS idea_decisions;
ALTER TABLE idea_decisions_new RENAME TO idea_decisions;

-- cemetery_entries: add FK to ideas
CREATE TABLE IF NOT EXISTS cemetery_entries_new (
    cemetery_id TEXT PRIMARY KEY,
    idea_id TEXT NOT NULL UNIQUE REFERENCES ideas(idea_id),
    reason_code TEXT NOT NULL,
    assumptions_json TEXT,
    revisit_triggers_json TEXT,
    buried_at TEXT NOT NULL,
    next_review_at TEXT,
    revived_at TEXT,
    status TEXT NOT NULL DEFAULT 'DORMANT'
);
INSERT OR IGNORE INTO cemetery_entries_new SELECT * FROM cemetery_entries;
DROP TABLE IF EXISTS cemetery_entries;
ALTER TABLE cemetery_entries_new RENAME TO cemetery_entries;

-- products: add FK to ideas
CREATE TABLE IF NOT EXISTS products_new (
    product_id TEXT PRIMARY KEY,
    idea_id TEXT REFERENCES ideas(idea_id),
    factory_id TEXT,
    factory_version TEXT,
    name TEXT NOT NULL,
    slug TEXT,
    product_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'BUILDING',
    build_run_id TEXT,
    certificate_id TEXT,
    domain TEXT,
    repository_url TEXT,
    deployment_url TEXT,
    released_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
INSERT OR IGNORE INTO products_new SELECT * FROM products;
DROP TABLE IF EXISTS products;
ALTER TABLE products_new RENAME TO products;

-- factory_genomes: add FK to products
CREATE TABLE IF NOT EXISTS factory_genomes_new (
    genome_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    genome_hash TEXT NOT NULL,
    genome_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
INSERT OR IGNORE INTO factory_genomes_new SELECT * FROM factory_genomes;
DROP TABLE IF EXISTS factory_genomes;
ALTER TABLE factory_genomes_new RENAME TO factory_genomes;

-- domains: add FK to products
CREATE TABLE IF NOT EXISTS domains_new (
    domain_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    domain_name TEXT NOT NULL,
    registrar TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    purchased_at TEXT,
    expires_at TEXT,
    created_at TEXT NOT NULL
);
INSERT OR IGNORE INTO domains_new SELECT * FROM domains;
DROP TABLE IF EXISTS domains;
ALTER TABLE domains_new RENAME TO domains;

-- publications: add FK to products and distribution_surfaces
CREATE TABLE IF NOT EXISTS publications_new (
    publication_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    surface_id TEXT NOT NULL REFERENCES distribution_surfaces(surface_id),
    status TEXT NOT NULL,
    external_ref TEXT,
    evidence_json TEXT,
    published_at TEXT,
    created_at TEXT NOT NULL
);
INSERT OR IGNORE INTO publications_new SELECT * FROM publications;
DROP TABLE IF EXISTS publications;
ALTER TABLE publications_new RENAME TO publications;

-- outcome_events: add FK to products
CREATE TABLE IF NOT EXISTS outcome_events_new (
    outcome_event_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    metric TEXT NOT NULL,
    value REAL,
    text_value TEXT,
    unit TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    occurred_at TEXT NOT NULL,
    evidence_json TEXT,
    created_at TEXT NOT NULL
);
INSERT OR IGNORE INTO outcome_events_new SELECT * FROM outcome_events;
DROP TABLE IF EXISTS outcome_events;
ALTER TABLE outcome_events_new RENAME TO outcome_events;

-- human_actions: add FKs to products, factory_runs, work_nodes
CREATE TABLE IF NOT EXISTS human_actions_new (
    action_id TEXT PRIMARY KEY,
    product_id TEXT REFERENCES products(product_id),
    factory_run_id TEXT REFERENCES factory_runs(factory_run_id),
    work_node_id TEXT REFERENCES work_nodes(node_id),
    action_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'REQUESTED',
    title TEXT,
    instructions_json TEXT,
    estimated_cost_usd REAL,
    decided_at TEXT,
    decision_json TEXT,
    completed_at TEXT,
    result_json TEXT,
    requested_at TEXT NOT NULL,
    idempotency_key TEXT UNIQUE
);
INSERT OR IGNORE INTO human_actions_new SELECT * FROM human_actions;
DROP TABLE IF EXISTS human_actions;
ALTER TABLE human_actions_new RENAME TO human_actions;

-- HotSwap: route_posteriors has natural composite PK, no additional FKs needed
-- route_definitions is a standalone lookup table, no FKs needed
