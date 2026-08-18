-- QDW federation substrate.
-- Final migration number must be the next unused number in the real checkout.
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS external_systems (
    system_id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    protocol_version TEXT NOT NULL,
    base_url TEXT,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
    trust_policy_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS external_sync_cursors (
    system_id TEXT NOT NULL REFERENCES external_systems(system_id),
    stream TEXT NOT NULL,
    cursor TEXT NOT NULL,
    source_revision TEXT,
    last_batch_digest TEXT,
    last_success_at TEXT,
    last_error_json TEXT,
    PRIMARY KEY(system_id,stream)
);

CREATE TABLE IF NOT EXISTS external_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    system_id TEXT NOT NULL REFERENCES external_systems(system_id),
    snapshot_kind TEXT NOT NULL,
    protocol_version TEXT NOT NULL,
    request_digest TEXT NOT NULL,
    response_digest TEXT NOT NULL,
    raw_artifact_id TEXT REFERENCES artifacts(artifact_id),
    external_status TEXT NOT NULL CHECK(external_status IN (
      'OK','OK_EMPTY','DEGRADED','STALE','UNAVAILABLE','INCOMPATIBLE_PROTOCOL',
      'UNAUTHORIZED','BUDGET_BLOCKED','POLICY_BLOCKED','FAILED'
    )),
    fetched_at TEXT NOT NULL,
    freshness_deadline TEXT,
    source_revision TEXT,
    adapter_version TEXT NOT NULL,
    normalized_digest TEXT NOT NULL,
    warning_json TEXT NOT NULL DEFAULT '[]',
    UNIQUE(system_id,response_digest,adapter_version)
);
CREATE INDEX IF NOT EXISTS idx_external_snapshots_system_kind_time
  ON external_snapshots(system_id,snapshot_kind,fetched_at);

CREATE TABLE IF NOT EXISTS federated_refs (
    federated_ref_id TEXT PRIMARY KEY,
    system_id TEXT NOT NULL REFERENCES external_systems(system_id),
    object_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    object_version TEXT,
    object_revision TEXT,
    object_digest TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    UNIQUE(system_id,object_type,object_id,object_version,object_revision,object_digest)
);
CREATE INDEX IF NOT EXISTS idx_federated_refs_lookup
  ON federated_refs(system_id,object_type,object_id);

CREATE TABLE IF NOT EXISTS external_object_mappings (
    mapping_id TEXT PRIMARY KEY,
    local_object_type TEXT NOT NULL,
    local_object_id TEXT NOT NULL,
    federated_ref_id TEXT NOT NULL REFERENCES federated_refs(federated_ref_id),
    relation TEXT NOT NULL CHECK(relation IN (
      'IDENTICAL','ALIAS','DERIVED_FROM','OBSERVES','EXECUTES','PROVIDES','PROPOSAL_FOR'
    )),
    confidence REAL CHECK(confidence IS NULL OR (confidence>=0 AND confidence<=1)),
    evidence_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    retired_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_external_mapping_local
  ON external_object_mappings(local_object_type,local_object_id);

CREATE TABLE IF NOT EXISTS external_advisories (
    advisory_id TEXT PRIMARY KEY,
    system_id TEXT NOT NULL REFERENCES external_systems(system_id),
    advisory_kind TEXT NOT NULL,
    snapshot_id TEXT REFERENCES external_snapshots(snapshot_id),
    external_object_id TEXT NOT NULL,
    method TEXT NOT NULL,
    advisory_json TEXT NOT NULL,
    advisory_digest TEXT NOT NULL UNIQUE,
    as_of TEXT NOT NULL,
    authority TEXT NOT NULL DEFAULT 'ADVISORY' CHECK(authority='ADVISORY')
);



-- Generalize HotSwap pricing so per-call Forge capabilities can participate without fabricating token prices.
-- Add fixed_request_cost_usd if not present
-- (idempotent: ALTER TABLE ADD COLUMN is not, but we check first)
-- This is handled by the application layer checking column existence.

CREATE TABLE IF NOT EXISTS federation_route_bindings (
    route_id TEXT PRIMARY KEY REFERENCES route_definitions(route_id) ON DELETE CASCADE,
    route_kind TEXT NOT NULL CHECK(route_kind IN ('DELL_INFERENCE','FORGE_CAPABILITY','LOCAL','OTHER_EXTERNAL')),
    federated_ref_id TEXT NOT NULL REFERENCES federated_refs(federated_ref_id),
    source_snapshot_id TEXT REFERENCES external_snapshots(snapshot_id),
    source_advisory_id TEXT REFERENCES external_advisories(advisory_id),
    external_profile_json TEXT NOT NULL DEFAULT '{}',
    binding_digest TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS federation_invocations (
    federation_invocation_id TEXT PRIMARY KEY,
    work_node_id TEXT REFERENCES work_nodes(node_id),
    factory_run_id TEXT REFERENCES factory_runs(factory_run_id),
    external_system_id TEXT NOT NULL REFERENCES external_systems(system_id),
    external_invocation_ref_id TEXT NOT NULL REFERENCES federated_refs(federated_ref_id),
    selected_asset_ref_id TEXT REFERENCES federated_refs(federated_ref_id),
    qdw_route_digest TEXT NOT NULL,
    request_digest TEXT NOT NULL,
    output_digest TEXT,
    nested_route_digest TEXT,
    status TEXT NOT NULL CHECK(status IN (
      'ACCEPTED','RUNNING','SUCCEEDED_UNVERIFIED','FAILED','VERIFIED','REJECTED'
    )),
    cost_usd REAL CHECK(cost_usd IS NULL OR cost_usd>=0),
    created_at TEXT NOT NULL,
    finished_at TEXT,
    UNIQUE(external_system_id,external_invocation_ref_id)
);

CREATE TABLE IF NOT EXISTS federation_certificate_bindings (
    binding_id TEXT PRIMARY KEY,
    federation_invocation_id TEXT NOT NULL REFERENCES federation_invocations(federation_invocation_id),
    issuer_system TEXT NOT NULL,
    certificate_id TEXT NOT NULL,
    certificate_digest TEXT NOT NULL,
    subject_digest TEXT NOT NULL,
    output_digest TEXT NOT NULL,
    policy_digest TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('VERIFIED','REJECTED')),
    bound_at TEXT NOT NULL,
    UNIQUE(issuer_system,certificate_id)
);

CREATE TABLE IF NOT EXISTS federation_health_events (
    health_event_id TEXT PRIMARY KEY,
    system_id TEXT NOT NULL REFERENCES external_systems(system_id),
    status TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    observed_at TEXT NOT NULL
);

-- Deal routes: Dell deals + LiteLLM baseline pricing
CREATE TABLE IF NOT EXISTS deal_routes (
    deal_route_id TEXT PRIMARY KEY,
    route_id TEXT NOT NULL UNIQUE,
    model_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    deal_score REAL NOT NULL DEFAULT 0,
    litellm_model TEXT,
    fixed_cost_usd REAL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Forge leases and invocations
CREATE TABLE IF NOT EXISTS forge_leases (
    lease_id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    version TEXT NOT NULL,
    capability TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    max_spend_usd REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS forge_invocation_certs (
    invocation_id TEXT NOT NULL,
    certificate_id TEXT NOT NULL,
    certificate_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
