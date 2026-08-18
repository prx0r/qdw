-- QDW 0006: canonical verification-plan and certificate bindings.

PRAGMA foreign_keys=ON;

CREATE TABLE verification_plans_v2 (
    plan_id TEXT NOT NULL,
    version TEXT NOT NULL,
    plan_hash TEXT NOT NULL UNIQUE,
    plan_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('CANDIDATE','ACTIVE','RETIRED')),
    created_at TEXT NOT NULL,
    PRIMARY KEY(plan_id, version)
);

CREATE TABLE verification_runs_v2 (
    verification_run_id TEXT PRIMARY KEY,
    plan_hash TEXT NOT NULL REFERENCES verification_plans_v2(plan_hash),
    task_id TEXT NOT NULL,
    subject_git_sha TEXT NOT NULL,
    subject_dirty INTEGER NOT NULL CHECK(subject_dirty IN (0,1)),
    cwd TEXT NOT NULL,
    environment_hash TEXT NOT NULL,
    artifact_set_json TEXT,
    artifact_set_hash TEXT,
    status TEXT NOT NULL CHECK(status IN ('RUNNING','PASS','FAIL','UNVERIFIED','BLOCKED')),
    started_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE verification_receipts_v2 (
    receipt_id TEXT PRIMARY KEY,
    verification_run_id TEXT NOT NULL REFERENCES verification_runs_v2(verification_run_id) ON DELETE CASCADE,
    command_id TEXT NOT NULL,
    argv_json TEXT NOT NULL,
    cwd TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    exit_code INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PASS','FAIL','UNVERIFIED','BLOCKED')),
    stdout_path TEXT NOT NULL,
    stderr_path TEXT NOT NULL,
    stdout_sha256 TEXT NOT NULL,
    stderr_sha256 TEXT NOT NULL,
    UNIQUE(verification_run_id, command_id)
);

CREATE TABLE build_certificates_v2 (
    build_certificate_id TEXT PRIMARY KEY,
    verification_run_id TEXT NOT NULL UNIQUE REFERENCES verification_runs_v2(verification_run_id),
    subject_git_sha TEXT NOT NULL,
    plan_hash TEXT NOT NULL,
    artifact_set_hash TEXT NOT NULL,
    ledger_root TEXT,
    certificate_json TEXT NOT NULL,
    certificate_hash TEXT NOT NULL UNIQUE,
    issued_at TEXT NOT NULL
);

CREATE TABLE fixture_certificates (
    fixture_certificate_id TEXT PRIMARY KEY,
    subject_type TEXT NOT NULL CHECK(subject_type IN ('factory','contractor')),
    subject_id TEXT NOT NULL,
    subject_version TEXT NOT NULL,
    definition_hash TEXT NOT NULL,
    fixture_id TEXT NOT NULL,
    factory_run_id TEXT REFERENCES factory_runs(factory_run_id),
    artifact_set_hash TEXT NOT NULL,
    acceptance_plan_hash TEXT NOT NULL,
    build_certificate_id TEXT REFERENCES build_certificates_v2(build_certificate_id),
    independent_worker_id TEXT,
    status TEXT NOT NULL CHECK(status IN ('ACCEPTED','REJECTED','REVOKED')),
    certificate_json TEXT NOT NULL,
    certificate_hash TEXT NOT NULL UNIQUE,
    issued_at TEXT NOT NULL
);

CREATE INDEX idx_fixture_subject ON fixture_certificates(
    subject_type,subject_id,subject_version,status
);

CREATE TABLE release_authorizations (
    release_authorization_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    build_run_id TEXT NOT NULL REFERENCES factory_runs(factory_run_id),
    artifact_set_hash TEXT NOT NULL,
    build_certificate_id TEXT NOT NULL REFERENCES build_certificates_v2(build_certificate_id),
    review_certificate_id TEXT REFERENCES review_certificates(review_certificate_id),
    policy_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('AUTHORIZED','REJECTED','REVOKED')),
    authorization_json TEXT NOT NULL,
    authorization_hash TEXT NOT NULL UNIQUE,
    issued_at TEXT NOT NULL
);

CREATE TABLE work_attempts (
    attempt_id TEXT PRIMARY KEY,
    node_id TEXT NOT NULL REFERENCES work_nodes(node_id) ON DELETE CASCADE,
    attempt_no INTEGER NOT NULL,
    worker_id TEXT,
    executor_id TEXT,
    route_id TEXT,
    lease_started_at TEXT,
    lease_until TEXT,
    started_at TEXT,
    finished_at TEXT,
    status TEXT NOT NULL CHECK(status IN (
        'LEASED','RUNNING','VERIFYING','SUCCEEDED','FAILED','EXPIRED','CANCELLED'
    )),
    failure_hash TEXT,
    result_hash TEXT,
    UNIQUE(node_id, attempt_no)
);

ALTER TABLE work_graphs ADD COLUMN structure_hash TEXT;
ALTER TABLE work_graphs ADD COLUMN frozen_at TEXT;
ALTER TABLE work_graphs ADD COLUMN graph_revision INTEGER NOT NULL DEFAULT 1;

ALTER TABLE products ADD COLUMN release_authorization_id TEXT;
ALTER TABLE outcome_events ADD COLUMN authority TEXT;
ALTER TABLE outcome_events ADD COLUMN learning_eligible INTEGER NOT NULL DEFAULT 0;

ALTER TABLE human_actions ADD COLUMN request_payload_hash TEXT;
ALTER TABLE human_actions ADD COLUMN decision_actor TEXT;
ALTER TABLE human_actions ADD COLUMN approved_payload_hash TEXT;
