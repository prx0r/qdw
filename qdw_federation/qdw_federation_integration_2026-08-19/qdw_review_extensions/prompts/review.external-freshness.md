# review.external-freshness

External snapshot time/freshness/outage semantics.

Review the exact QDW SHA and every pinned external repository affected by the change.

Mandatory checks:
- ERROR != OK_EMPTY
- stale policy explicit
- cached response digest retained

Rules:
- external README/commit claims are not evidence;
- a foreign recommendation is not QDW authority;
- a valid external certificate for the wrong subject is invalid;
- external failure cannot be translated to an empty successful result;
- report exact repository + SHA + path for cross-repo findings;
- create executable contract/attack tests where possible;
- reviewer cannot modify source or certify its own findings.
