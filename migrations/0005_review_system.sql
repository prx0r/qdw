-- QDW 0005: native autonomous review subsystem.
-- Apply only after migration runner atomicity/digest baselining is fixed.

PRAGMA foreign_keys=ON;

CREATE TABLE review_runs (
    review_run_id TEXT PRIMARY KEY,
    subject_git_sha TEXT NOT NULL,
    subject_dirty INTEGER NOT NULL CHECK(subject_dirty IN (0,1)),
    base_git_sha TEXT,
    policy_id TEXT NOT NULL,
    policy_hash TEXT NOT NULL,
    profile TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    changed_paths_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN (
        'PLANNED','SCANNING','REVIEWING','ATTACKING','NEEDS_FIX',
        'WAITING_FIX','VERIFYING','READY_TO_CERTIFY','CERTIFIED',
        'REJECTED','STALLED','BLOCKED','FAILED'
    )),
    current_round INTEGER NOT NULL DEFAULT 0,
    max_rounds INTEGER NOT NULL,
    max_cost_usd REAL,
    spent_cost_usd REAL NOT NULL DEFAULT 0,
    producer_worker_id TEXT,
    fix_graph_id TEXT REFERENCES work_graphs(graph_id),
    blocker_set_hash TEXT,
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE INDEX idx_review_runs_subject ON review_runs(subject_git_sha, status);

CREATE TABLE review_rounds (
    review_round_id TEXT PRIMARY KEY,
    review_run_id TEXT NOT NULL REFERENCES review_runs(review_run_id) ON DELETE CASCADE,
    round_no INTEGER NOT NULL,
    subject_git_sha TEXT NOT NULL,
    policy_hash TEXT NOT NULL,
    reviewer_set_hash TEXT NOT NULL,
    attack_set_hash TEXT NOT NULL,
    blocker_set_hash TEXT,
    cost_usd REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    UNIQUE(review_run_id, round_no)
);

CREATE TABLE review_module_runs (
    module_run_id TEXT PRIMARY KEY,
    review_round_id TEXT NOT NULL REFERENCES review_rounds(review_round_id) ON DELETE CASCADE,
    reviewer_id TEXT NOT NULL,
    reviewer_version TEXT NOT NULL,
    reviewer_definition_hash TEXT NOT NULL,
    work_node_id TEXT REFERENCES work_nodes(node_id),
    worker_id TEXT,
    executor_id TEXT,
    route_id TEXT,
    output_artifact_id TEXT REFERENCES artifacts(artifact_id),
    status TEXT NOT NULL CHECK(status IN ('PENDING','RUNNING','PASS','FAIL','UNVERIFIED','BLOCKED')),
    cost_usd REAL NOT NULL DEFAULT 0,
    started_at TEXT,
    finished_at TEXT,
    UNIQUE(review_round_id, reviewer_id, reviewer_version)
);

CREATE TABLE review_findings (
    finding_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    review_run_id TEXT NOT NULL REFERENCES review_runs(review_run_id) ON DELETE CASCADE,
    review_round_id TEXT NOT NULL REFERENCES review_rounds(review_round_id) ON DELETE CASCADE,
    module_run_id TEXT REFERENCES review_module_runs(module_run_id) ON DELETE SET NULL,
    rule_id TEXT NOT NULL,
    module_id TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('CRITICAL','HIGH','MEDIUM','LOW','INFO')),
    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    status TEXT NOT NULL CHECK(status IN (
        'OPEN','ACKNOWLEDGED','FIXED','REGRESSION','SUPPRESSED','WONT_FIX'
    )),
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    invariant_text TEXT NOT NULL,
    remediation TEXT,
    first_seen_sha TEXT NOT NULL,
    last_seen_sha TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_review_findings_run ON review_findings(review_run_id,severity,status);
CREATE INDEX idx_review_findings_fp ON review_findings(fingerprint,status);

CREATE TABLE review_evidence (
    evidence_id TEXT PRIMARY KEY,
    finding_id TEXT NOT NULL REFERENCES review_findings(finding_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    path TEXT,
    line INTEGER,
    detail TEXT,
    content_sha256 TEXT,
    verification_run_id TEXT,
    receipt_id TEXT,
    artifact_id TEXT REFERENCES artifacts(artifact_id),
    created_at TEXT NOT NULL
);

CREATE TABLE review_acceptance_specs (
    acceptance_spec_id TEXT PRIMARY KEY,
    finding_fingerprint TEXT NOT NULL,
    spec_hash TEXT NOT NULL UNIQUE,
    spec_json TEXT NOT NULL,
    frozen_at TEXT NOT NULL,
    frozen_subject_sha TEXT NOT NULL
);

CREATE TABLE review_finding_acceptance (
    finding_id TEXT NOT NULL REFERENCES review_findings(finding_id) ON DELETE CASCADE,
    acceptance_spec_id TEXT NOT NULL REFERENCES review_acceptance_specs(acceptance_spec_id),
    verification_run_id TEXT,
    status TEXT NOT NULL CHECK(status IN ('PENDING','PASS','FAIL','UNVERIFIED','BLOCKED')),
    checked_at TEXT,
    PRIMARY KEY(finding_id, acceptance_spec_id)
);

CREATE TABLE review_attack_results (
    attack_result_id TEXT PRIMARY KEY,
    review_round_id TEXT NOT NULL REFERENCES review_rounds(review_round_id) ON DELETE CASCADE,
    attack_id TEXT NOT NULL,
    attack_version TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PASS','FAIL','UNVERIFIED','BLOCKED')),
    expected_reason_code TEXT,
    actual_reason_code TEXT,
    verification_run_id TEXT,
    receipt_id TEXT,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(review_round_id, attack_id, attack_version)
);

CREATE TABLE review_suppressions (
    suppression_id TEXT PRIMARY KEY,
    finding_fingerprint TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    subject_git_sha TEXT,
    reason TEXT NOT NULL,
    approved_by TEXT NOT NULL,
    approved_at TEXT NOT NULL,
    expires_at TEXT
);

CREATE TABLE review_certificates (
    review_certificate_id TEXT PRIMARY KEY,
    review_run_id TEXT NOT NULL UNIQUE REFERENCES review_runs(review_run_id),
    subject_git_sha TEXT NOT NULL,
    policy_hash TEXT NOT NULL,
    report_hash TEXT NOT NULL,
    reviewer_set_hash TEXT NOT NULL,
    attack_set_hash TEXT NOT NULL,
    certifier_worker_id TEXT NOT NULL,
    producer_worker_id TEXT,
    status TEXT NOT NULL CHECK(status IN ('REVIEW_CERTIFIED','REVIEW_REJECTED')),
    certificate_json TEXT NOT NULL,
    certificate_hash TEXT NOT NULL UNIQUE,
    signature_b64 TEXT,
    issued_at TEXT NOT NULL
);

CREATE TABLE review_pack_exports (
    export_id TEXT PRIMARY KEY,
    review_run_id TEXT NOT NULL REFERENCES review_runs(review_run_id) ON DELETE CASCADE,
    artifact_path TEXT NOT NULL,
    artifact_sha256 TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    file_count INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
