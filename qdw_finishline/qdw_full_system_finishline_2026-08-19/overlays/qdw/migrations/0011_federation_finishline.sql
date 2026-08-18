-- QDW 0011: finish real federation runtime and remove fake-Forge state ownership.
PRAGMA foreign_keys=ON;

ALTER TABLE route_definitions ADD COLUMN fixed_request_cost_usd REAL
  CHECK(fixed_request_cost_usd IS NULL OR fixed_request_cost_usd >= 0);

-- Preserve only non-secret historical facts from the local fake Forge tables introduced in 0010.
CREATE TABLE legacy_forge_lease_receipts_0010 (
  lease_id TEXT PRIMARY KEY,
  asset_id TEXT NOT NULL,
  version TEXT NOT NULL,
  capability TEXT NOT NULL,
  max_spend_usd REAL,
  created_at TEXT NOT NULL,
  retired_reason TEXT NOT NULL DEFAULT 'QDW_DOES_NOT_OWN_FORGE_LEASES'
);
INSERT OR IGNORE INTO legacy_forge_lease_receipts_0010(
  lease_id,asset_id,version,capability,max_spend_usd,created_at
)
SELECT lease_id,asset_id,version,capability,max_spend_usd,created_at FROM forge_leases;
DROP TABLE forge_leases;

CREATE TABLE legacy_forge_certificate_receipts_0010 (
  invocation_id TEXT NOT NULL,
  certificate_id TEXT NOT NULL,
  certificate_hash TEXT,
  status TEXT,
  created_at TEXT NOT NULL,
  retired_reason TEXT NOT NULL DEFAULT 'REPLACED_BY_FEDERATION_CERTIFICATE_BINDING',
  PRIMARY KEY(invocation_id,certificate_id)
);
INSERT OR IGNORE INTO legacy_forge_certificate_receipts_0010(
  invocation_id,certificate_id,certificate_hash,status,created_at
)
SELECT invocation_id,certificate_id,certificate_hash,status,created_at FROM forge_invocation_certs;
DROP TABLE forge_invocation_certs;

CREATE TABLE federation_attempts_v2 (
  attempt_id TEXT PRIMARY KEY,
  work_node_id TEXT REFERENCES work_nodes(node_id),
  factory_run_id TEXT REFERENCES factory_runs(factory_run_id),
  task_cell_id TEXT,
  capability TEXT NOT NULL,
  request_digest TEXT NOT NULL,
  request_json TEXT NOT NULL,
  state TEXT NOT NULL CHECK(state IN (
    'DISCOVERING','CANDIDATES_READY','ROUTED','LEASED','RUNNING',
    'SUCCEEDED_UNVERIFIED','VERIFYING','VERIFIED','COMMITTED','FAILED'
  )),
  route_id TEXT REFERENCES route_definitions(route_id),
  route_binding_digest TEXT,
  external_lease_id TEXT,
  external_invocation_id TEXT,
  external_output_digest TEXT,
  quoted_cost_usd REAL CHECK(quoted_cost_usd IS NULL OR quoted_cost_usd >= 0),
  actual_cost_usd REAL CHECK(actual_cost_usd IS NULL OR actual_cost_usd >= 0),
  certificate_id TEXT,
  cost_event_id TEXT REFERENCES cost_events(cost_event_id),
  learning_event_id TEXT,
  failure_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX idx_federation_attempts_state ON federation_attempts_v2(state,updated_at);
CREATE INDEX idx_federation_attempts_node ON federation_attempts_v2(work_node_id,state);

CREATE TABLE federation_certificates_v2 (
  certificate_id TEXT PRIMARY KEY,
  issuer_system TEXT NOT NULL CHECK(issuer_system='qdw'),
  subject_system TEXT NOT NULL,
  subject_type TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  subject_digest TEXT,
  output_digest TEXT NOT NULL,
  policy_id TEXT NOT NULL,
  policy_hash TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('VERIFIED','REJECTED')),
  certificate_json TEXT NOT NULL,
  certificate_hash TEXT NOT NULL UNIQUE,
  issued_at TEXT NOT NULL,
  UNIQUE(subject_system,subject_type,subject_id,policy_hash,output_digest)
);

CREATE TABLE federation_learning_effects (
  learning_event_id TEXT PRIMARY KEY,
  attempt_id TEXT NOT NULL UNIQUE REFERENCES federation_attempts_v2(attempt_id),
  cell_id TEXT NOT NULL,
  route_id TEXT NOT NULL REFERENCES route_definitions(route_id),
  success INTEGER NOT NULL CHECK(success IN (0,1)),
  weight REAL NOT NULL CHECK(weight > 0),
  applied_at TEXT NOT NULL
);

CREATE TABLE federation_sync_receipts (
  sync_receipt_id TEXT PRIMARY KEY,
  system_id TEXT NOT NULL REFERENCES external_systems(system_id),
  stream TEXT NOT NULL,
  request_digest TEXT NOT NULL,
  snapshot_id TEXT REFERENCES external_snapshots(snapshot_id),
  external_status TEXT NOT NULL,
  cursor_before TEXT,
  cursor_after TEXT,
  inserted_count INTEGER NOT NULL DEFAULT 0,
  duplicate_count INTEGER NOT NULL DEFAULT 0,
  started_at TEXT NOT NULL,
  finished_at TEXT NOT NULL
);


CREATE TABLE external_opportunity_proposals (
  proposal_id TEXT PRIMARY KEY,
  system_id TEXT NOT NULL REFERENCES external_systems(system_id),
  external_object_id TEXT NOT NULL,
  external_object_digest TEXT NOT NULL,
  snapshot_id TEXT NOT NULL REFERENCES external_snapshots(snapshot_id),
  authority TEXT NOT NULL DEFAULT 'ADVISORY' CHECK(authority='ADVISORY'),
  problem_text TEXT,
  proposal_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'UNASSESSED'
    CHECK(status IN ('UNASSESSED','INGESTED_AS_EVIDENCE','DISMISSED','SUPERSEDED')),
  created_at TEXT NOT NULL,
  UNIQUE(system_id,external_object_id,external_object_digest)
);

CREATE TABLE federation_protocol_pins (
  system_id TEXT PRIMARY KEY REFERENCES external_systems(system_id),
  protocol_version TEXT NOT NULL,
  source_repository TEXT NOT NULL,
  source_git_sha TEXT NOT NULL,
  compatibility_hash TEXT NOT NULL,
  pinned_at TEXT NOT NULL
);
