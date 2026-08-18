PRAGMA foreign_keys=ON;

-- Mutable activation is separate from immutable asset manifest.
CREATE TABLE IF NOT EXISTS asset_activations_v2(
  asset_id TEXT NOT NULL,
  version TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('CANDIDATE','ACTIVE','PAUSED','RETIRED')),
  certificate_id TEXT,
  certificate_hash TEXT,
  activated_at TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(asset_id,version),
  FOREIGN KEY(asset_id,version) REFERENCES assets(asset_id,version) ON DELETE CASCADE
);
INSERT OR IGNORE INTO asset_activations_v2(
  asset_id,version,status,certificate_id,updated_at
)
SELECT asset_id,version,status,certificate_id,created_at FROM assets;

-- Source provenance is append-only and commit-pinned.
CREATE TABLE IF NOT EXISTS asset_source_bindings(
  source_binding_id TEXT PRIMARY KEY,
  asset_id TEXT NOT NULL,
  version TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  repository_uri TEXT NOT NULL,
  source_commit TEXT NOT NULL,
  manifest_path TEXT NOT NULL,
  manifest_digest TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  UNIQUE(asset_id,version,repository_uri,source_commit,manifest_path,manifest_digest),
  FOREIGN KEY(asset_id,version) REFERENCES assets(asset_id,version) ON DELETE CASCADE
);

-- Stable authenticated client identity.
ALTER TABLE leases ADD COLUMN client_id TEXT NOT NULL DEFAULT 'legacy';

-- Rebuild invocation table: idempotency is scoped to authenticated client identity, not globally.
ALTER TABLE invocations RENAME TO invocations_legacy_0001;
CREATE TABLE invocations(
  invocation_id TEXT PRIMARY KEY,
  client_id TEXT NOT NULL,
  client_request_id TEXT NOT NULL,
  lease_id TEXT NOT NULL,
  capability TEXT NOT NULL,
  asset_id TEXT NOT NULL,
  version TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  status TEXT NOT NULL,
  output_json TEXT,
  output_hash TEXT,
  quoted_cost_usd REAL NOT NULL DEFAULT 0 CHECK(quoted_cost_usd>=0),
  actual_cost_usd REAL CHECK(actual_cost_usd IS NULL OR actual_cost_usd>=0),
  billable_cost_usd REAL NOT NULL DEFAULT 0 CHECK(billable_cost_usd>=0),
  pricing_violation INTEGER NOT NULL DEFAULT 0 CHECK(pricing_violation IN (0,1)),
  route_json TEXT,
  verification_certificate_id TEXT,
  failure TEXT,
  created_at TEXT NOT NULL,
  finished_at TEXT,
  UNIQUE(client_id,client_request_id),
  FOREIGN KEY(lease_id) REFERENCES leases(lease_id),
  FOREIGN KEY(asset_id,version) REFERENCES assets(asset_id,version)
);
INSERT INTO invocations(
  invocation_id,client_id,client_request_id,lease_id,capability,asset_id,version,input_hash,status,
  output_json,output_hash,quoted_cost_usd,actual_cost_usd,billable_cost_usd,pricing_violation,
  route_json,verification_certificate_id,failure,created_at,finished_at
)
SELECT invocation_id,'legacy',client_request_id,lease_id,capability,asset_id,version,input_hash,status,
       output_json,output_hash,cost_usd,cost_usd,cost_usd,0,route_json,
       verification_certificate_id,failure,created_at,finished_at
FROM invocations_legacy_0001;
DROP TABLE invocations_legacy_0001;

CREATE TABLE IF NOT EXISTS verification_applications(
  certificate_id TEXT PRIMARY KEY,
  certificate_hash TEXT NOT NULL UNIQUE,
  issuer_system TEXT NOT NULL,
  invocation_id TEXT NOT NULL UNIQUE REFERENCES invocations(invocation_id),
  subject_output_hash TEXT NOT NULL,
  policy_hash TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('VERIFIED','REJECTED')),
  applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS forgejo_sync_receipts(
  sync_receipt_id TEXT PRIMARY KEY,
  forgejo_base_url TEXT NOT NULL,
  org TEXT NOT NULL,
  repo_name TEXT NOT NULL,
  source_commit TEXT,
  manifest_path TEXT NOT NULL DEFAULT 'qdw.yaml',
  manifest_digest TEXT,
  status TEXT NOT NULL CHECK(status IN ('REGISTERED','NO_MANIFEST','ERROR')),
  error_code TEXT,
  error_detail TEXT,
  observed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schema_versions(
  version INTEGER PRIMARY KEY,
  filename TEXT NOT NULL UNIQUE,
  content_hash TEXT NOT NULL,
  applied_at TEXT NOT NULL
);
