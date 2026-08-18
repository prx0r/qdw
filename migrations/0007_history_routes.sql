-- QDW 0007: append-only idea cemetery episodes + complete route persistence.

PRAGMA foreign_keys=ON;

CREATE TABLE cemetery_entries_v2 (
    cemetery_id TEXT PRIMARY KEY,
    idea_id TEXT NOT NULL REFERENCES ideas(idea_id),
    episode_no INTEGER NOT NULL,
    reason_code TEXT NOT NULL,
    assumptions_json TEXT,
    revisit_triggers_json TEXT,
    buried_at TEXT NOT NULL,
    next_review_at TEXT,
    revived_at TEXT,
    status TEXT NOT NULL DEFAULT 'DORMANT'
      CHECK(status IN ('DORMANT','REVIVED','SUPERSEDED')),
    supersedes_cemetery_id TEXT REFERENCES cemetery_entries_v2(cemetery_id),
    UNIQUE(idea_id, episode_no)
);

INSERT INTO cemetery_entries_v2(
    cemetery_id,idea_id,episode_no,reason_code,assumptions_json,revisit_triggers_json,
    buried_at,next_review_at,revived_at,status,supersedes_cemetery_id
)
SELECT cemetery_id,idea_id,1,reason_code,assumptions_json,revisit_triggers_json,
       buried_at,next_review_at,revived_at,status,NULL
FROM cemetery_entries;

DROP TABLE cemetery_entries;
ALTER TABLE cemetery_entries_v2 RENAME TO cemetery_entries;
CREATE INDEX idx_cemetery_idea_status ON cemetery_entries(idea_id,status,episode_no DESC);

ALTER TABLE route_definitions ADD COLUMN endpoint_id TEXT;
ALTER TABLE route_definitions ADD COLUMN account_id TEXT;
ALTER TABLE route_definitions ADD COLUMN prior_success REAL;
ALTER TABLE route_definitions ADD COLUMN prior_confidence REAL NOT NULL DEFAULT 0;
ALTER TABLE route_definitions ADD COLUMN breaker_open INTEGER NOT NULL DEFAULT 0;
ALTER TABLE route_definitions ADD COLUMN quota_pressure REAL NOT NULL DEFAULT 0;
ALTER TABLE route_definitions ADD COLUMN evidence_ids_json TEXT NOT NULL DEFAULT '[]';


ALTER TABLE idea_decisions ADD COLUMN evidence_ref TEXT;
ALTER TABLE idea_decisions ADD COLUMN reviewer_id TEXT;
ALTER TABLE idea_decisions ADD COLUMN reviewer_version TEXT;

CREATE TABLE idea_review_evidence (
    evidence_id TEXT PRIMARY KEY,
    idea_id TEXT NOT NULL REFERENCES ideas(idea_id),
    stage TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    reviewer_version TEXT NOT NULL,
    artifact_id TEXT REFERENCES artifacts(artifact_id),
    passed INTEGER NOT NULL CHECK(passed IN (0,1)),
    score_json TEXT NOT NULL,
    reason_codes_json TEXT NOT NULL,
    snapshot_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_idea_review_evidence ON idea_review_evidence(idea_id,stage,created_at);
