-- Durable proof that a finding was independently closed.
PRAGMA foreign_keys=ON;

CREATE TABLE review_finding_closures (
    closure_id TEXT PRIMARY KEY,
    finding_id TEXT NOT NULL UNIQUE REFERENCES review_findings(finding_id),
    finding_fingerprint TEXT NOT NULL,
    old_subject_git_sha TEXT NOT NULL,
    new_subject_git_sha TEXT NOT NULL,
    acceptance_set_hash TEXT NOT NULL,
    acceptance_verification_hash TEXT NOT NULL,
    recheck_review_round_id TEXT NOT NULL REFERENCES review_rounds(review_round_id),
    certifier_id TEXT NOT NULL,
    closure_json TEXT NOT NULL,
    closure_hash TEXT NOT NULL UNIQUE,
    closed_at TEXT NOT NULL
);
CREATE INDEX idx_review_closure_fp ON review_finding_closures(finding_fingerprint,new_subject_git_sha);
