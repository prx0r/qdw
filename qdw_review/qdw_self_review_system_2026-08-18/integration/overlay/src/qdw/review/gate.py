from __future__ import annotations

def require_review_certificate(db, subject_git_sha:str, policy_hash:str):
    """Release gate: resolve a REVIEW_CERTIFIED certificate bound to exact SHA and policy."""
    with db.connect() as con:
        r=con.execute("""SELECT * FROM review_certificates
            WHERE subject_git_sha=? AND policy_hash=? AND status='REVIEW_CERTIFIED'
            ORDER BY issued_at DESC LIMIT 1""",(subject_git_sha,policy_hash)).fetchone()
    if not r:
        raise ValueError("no valid review certificate for subject/policy")
    return dict(r)
