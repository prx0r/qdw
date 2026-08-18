-- QDW reviewer / self-peer-review substrate.
-- IMPORTANT: this must be a NEW migration. Never append it to 0002_global.sql.

PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS migration_digests (
    version INTEGER PRIMARY KEY,
    filename TEXT NOT NULL UNIQUE,
    sha256 TEXT NOT NULL,
    first_recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviewer_definitions (
    reviewer_id TEXT NOT NULL,
    version TEXT NOT NULL,
    definition_hash TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'CANDIDATE'
      CHECK(status IN ('CANDIDATE','ACTIVE','RETIRED')),
    created_at TEXT NOT NULL,
    PRIMARY KEY(reviewer_id, version)
);

CREATE TABLE IF NOT EXISTS review_runs (
    review_run_id TEXT PRIMARY KEY,
    subject_git_sha TEXT NOT NULL,
    git_dirty INTEGER NOT NULL CHECK(git_dirty IN (0,1)),
    policy_hash TEXT NOT NULL,
    profile TEXT NOT NULL,
    producer_run_id TEXT,
    status TEXT NOT NULL
      CHECK(status IN ('PLANNED','RUNNING','VERIFYING','CERTIFIED','REJECTED','FAILED','BLOCKED')),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    aggregate_report_hash TEXT
);

CREATE TABLE IF NOT EXISTS review_module_runs (
    module_run_id TEXT PRIMARY KEY,
    review_run_id TEXT NOT NULL REFERENCES review_runs(review_run_id) ON DELETE CASCADE,
    reviewer_id TEXT NOT NULL,
    reviewer_version TEXT NOT NULL,
    reviewer_definition_hash TEXT NOT NULL,
    worker_id TEXT,
    status TEXT NOT NULL
      CHECK(status IN ('PENDING','RUNNING','PASS','FAIL','UNVERIFIED','BLOCKED')),
    started_at TEXT,
    finished_at TEXT,
    output_hash TEXT,
    UNIQUE(review_run_id, reviewer_id, reviewer_version)
);

CREATE TABLE IF NOT EXISTS review_findings (
    finding_id TEXT PRIMARY KEY,
    review_run_id TEXT NOT NULL REFERENCES review_runs(review_run_id) ON DELETE CASCADE,
    module_run_id TEXT NOT NULL REFERENCES review_module_runs(module_run_id) ON DELETE CASCADE,
    rule_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('CRITICAL','HIGH','MEDIUM','LOW','INFO')),
    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    status TEXT NOT NULL DEFAULT 'OPEN'
      CHECK(status IN ('OPEN','ACKNOWLEDGED','FIXED','REGRESSION','SUPPRESSED','WONT_FIX')),
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    invariant_text TEXT NOT NULL,
    remediation TEXT,
    first_seen_sha TEXT,
    last_seen_sha TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_review_findings_run_sev
    ON review_findings(review_run_id, severity, status);
CREATE INDEX IF NOT EXISTS idx_review_findings_fingerprint
    ON review_findings(fingerprint);

CREATE TABLE IF NOT EXISTS review_evidence (
    evidence_id TEXT PRIMARY KEY,
    finding_id TEXT NOT NULL REFERENCES review_findings(finding_id) ON DELETE CASCADE,
    evidence_kind TEXT NOT NULL,
    path TEXT,
    line INTEGER,
    detail TEXT,
    content_sha256 TEXT,
    command_receipt_id TEXT,
    artifact_id TEXT REFERENCES artifacts(artifact_id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_acceptance_tests (
    acceptance_test_id TEXT PRIMARY KEY,
    finding_id TEXT NOT NULL REFERENCES review_findings(finding_id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    test_path TEXT,
    required_for_close INTEGER NOT NULL DEFAULT 1 CHECK(required_for_close IN (0,1))
);

CREATE TABLE IF NOT EXISTS review_suppressions (
    suppression_id TEXT PRIMARY KEY,
    finding_fingerprint TEXT NOT NULL,
    reason TEXT NOT NULL,
    approved_by TEXT NOT NULL,
    approved_at TEXT NOT NULL,
    expires_at TEXT,
    subject_git_sha TEXT
);

CREATE TABLE IF NOT EXISTS review_attack_runs (
    attack_run_id TEXT PRIMARY KEY,
    review_run_id TEXT NOT NULL REFERENCES review_runs(review_run_id) ON DELETE CASCADE,
    attack_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PASS','FAIL','UNVERIFIED','BLOCKED')),
    command_receipt_id TEXT,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(review_run_id, attack_id)
);

CREATE TABLE IF NOT EXISTS review_certificates (
    review_certificate_id TEXT PRIMARY KEY,
    review_run_id TEXT NOT NULL UNIQUE REFERENCES review_runs(review_run_id),
    subject_git_sha TEXT NOT NULL,
    policy_hash TEXT NOT NULL,
    aggregate_report_hash TEXT NOT NULL,
    reviewer_set_hash TEXT NOT NULL,
    attack_set_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('REVIEW_CERTIFIED','REVIEW_REJECTED')),
    certificate_json TEXT NOT NULL,
    certificate_hash TEXT NOT NULL UNIQUE,
    certifier_worker_id TEXT,
    issued_at TEXT NOT NULL,
    signature_b64 TEXT
);
