-- World state layer
CREATE TABLE IF NOT EXISTS source_connectors (
    source_id TEXT PRIMARY KEY,
    family TEXT NOT NULL,
    name TEXT NOT NULL,
    config_json TEXT,
    terms_url TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    external_key TEXT,
    attributes_json TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_entities_ext ON entities(kind, external_key) WHERE external_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS entity_aliases (
    entity_id TEXT NOT NULL REFERENCES entities(entity_id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    PRIMARY KEY(entity_id, alias)
);

CREATE TABLE IF NOT EXISTS observations (
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
CREATE INDEX IF NOT EXISTS idx_obs_source ON observations(source_id, source_item_id);

CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    observation_id TEXT,
    subject_entity_id TEXT,
    predicate TEXT NOT NULL,
    object_json TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    claim_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS relations (
    relation_id TEXT PRIMARY KEY,
    subject_entity_id TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_entity_id TEXT NOT NULL,
    supporting_claim_id TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_relations_unique
    ON relations(subject_entity_id, predicate, object_entity_id, supporting_claim_id);

-- Intelligence layer
CREATE TABLE IF NOT EXISTS pain_clusters (
    cluster_id TEXT PRIMARY KEY,
    problem_key TEXT NOT NULL UNIQUE,
    title TEXT,
    summary TEXT,
    mention_count INTEGER NOT NULL DEFAULT 0,
    source_family_count INTEGER NOT NULL DEFAULT 0,
    recurrence REAL DEFAULT 0,
    intensity REAL DEFAULT 0,
    solvability REAL DEFAULT 0,
    verifiability REAL DEFAULT 0,
    confidence REAL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pain_observations (
    pain_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL,
    text TEXT NOT NULL,
    normalized_text TEXT,
    fingerprint TEXT,
    intensity REAL NOT NULL DEFAULT 0.5,
    recurrence_hint REAL NOT NULL DEFAULT 0.5,
    workaround TEXT,
    willingness_to_pay REAL,
    machine_solvable REAL NOT NULL DEFAULT 0.5,
    verifiable REAL NOT NULL DEFAULT 0.5,
    cluster_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS startup_events (
    startup_event_id TEXT PRIMARY KEY,
    company_entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_at TEXT NOT NULL,
    amount_usd REAL,
    stage TEXT,
    attributes_json TEXT,
    observation_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS capabilities (
    capability_id TEXT PRIMARY KEY,
    capability_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resources (
    resource_id TEXT PRIMARY KEY,
    capability_id TEXT NOT NULL,
    provider_entity_id TEXT,
    resource_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    version TEXT,
    interface_kind TEXT,
    attributes_json TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resource_measurements (
    measurement_id TEXT PRIMARY KEY,
    resource_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL,
    text_value TEXT,
    unit TEXT,
    observed_at TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    observation_id TEXT,
    created_at TEXT NOT NULL
);

-- Opportunity / Idea layer
CREATE TABLE IF NOT EXISTS opportunities_global (
    opportunity_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    problem_key TEXT NOT NULL,
    title TEXT NOT NULL,
    thesis TEXT,
    factory_hint TEXT,
    status TEXT NOT NULL DEFAULT 'CANDIDATE',
    score_json TEXT,
    feature_snapshot_json TEXT,
    feature_snapshot_hash TEXT,
    evidence_snapshot_hash TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS opportunity_evidence (
    opportunity_id TEXT NOT NULL,
    observation_id TEXT,
    claim_id TEXT,
    pain_cluster_id TEXT,
    startup_event_id TEXT,
    resource_id TEXT,
    role TEXT NOT NULL DEFAULT 'support'
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_opp_ev_unique
    ON opportunity_evidence(opportunity_id, COALESCE(observation_id,'_'), COALESCE(claim_id,'_'), role);

CREATE TABLE IF NOT EXISTS ideas (
    idea_id TEXT PRIMARY KEY,
    opportunity_id TEXT,
    problem_key TEXT NOT NULL,
    solution_key TEXT NOT NULL,
    canonical_title TEXT NOT NULL,
    summary TEXT,
    customer TEXT,
    product_form TEXT,
    fingerprint TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'PROPOSED',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS idea_relations (
    relation_id TEXT PRIMARY KEY,
    from_idea_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    to_idea_id TEXT NOT NULL,
    rationale TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS idea_decisions (
    decision_id TEXT PRIMARY KEY,
    idea_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    decision TEXT NOT NULL,
    score_json TEXT,
    reason_codes_json TEXT,
    snapshot_hash TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cemetery_entries (
    cemetery_id TEXT PRIMARY KEY,
    idea_id TEXT NOT NULL UNIQUE,
    reason_code TEXT NOT NULL,
    assumptions_json TEXT,
    revisit_triggers_json TEXT,
    buried_at TEXT NOT NULL,
    next_review_at TEXT,
    revived_at TEXT,
    status TEXT NOT NULL DEFAULT 'DORMANT'
);

-- Human action queue
CREATE TABLE IF NOT EXISTS human_actions (
    action_id TEXT PRIMARY KEY,
    product_id TEXT,
    factory_run_id TEXT,
    work_node_id TEXT,
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

-- Watch triggers
CREATE TABLE IF NOT EXISTS watch_triggers (
    trigger_id TEXT PRIMARY KEY,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    condition_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    last_evaluated_at TEXT,
    last_result_json TEXT,
    created_at TEXT NOT NULL
);

-- Product layer
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    idea_id TEXT,
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

CREATE TABLE IF NOT EXISTS factory_genomes (
    genome_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    genome_hash TEXT NOT NULL,
    genome_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS domains (
    domain_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    domain_name TEXT NOT NULL,
    registrar TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    purchased_at TEXT,
    expires_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS distribution_surfaces (
    surface_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS publications (
    publication_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    surface_id TEXT NOT NULL,
    status TEXT NOT NULL,
    external_ref TEXT,
    evidence_json TEXT,
    published_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outcome_events (
    outcome_event_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL,
    text_value TEXT,
    unit TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    occurred_at TEXT NOT NULL,
    evidence_json TEXT,
    created_at TEXT NOT NULL
);

-- Contractor layer
CREATE TABLE IF NOT EXISTS contractor_definitions (
    contractor_id TEXT NOT NULL,
    version TEXT NOT NULL,
    definition_hash TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'CANDIDATE',
    created_at TEXT NOT NULL,
    PRIMARY KEY(contractor_id, version)
);
