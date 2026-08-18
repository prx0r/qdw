# review.external-trust

Certificate, lease, invocation, advisory and external object subject binding.

Review the exact QDW SHA and every pinned external repository affected by the change.

Mandatory checks:
- valid-unrelated evidence attacks
- no passed=true trust boundary
- issuer allowlist

Rules:
- external README/commit claims are not evidence;
- a foreign recommendation is not QDW authority;
- a valid external certificate for the wrong subject is invalid;
- external failure cannot be translated to an empty successful result;
- report exact repository + SHA + path for cross-repo findings;
- create executable contract/attack tests where possible;
- reviewer cannot modify source or certify its own findings.
