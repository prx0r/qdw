# review.sandbox-graduation

Ensure promoted Sandbox features have one production owner and donor authority is retired.

Review the exact QDW SHA and every pinned external repository affected by the change.

Mandatory checks:
- donor fixtures frozen
- target equivalence tested
- duplicate runtime disabled

Rules:
- external README/commit claims are not evidence;
- a foreign recommendation is not QDW authority;
- a valid external certificate for the wrong subject is invalid;
- external failure cannot be translated to an empty successful result;
- report exact repository + SHA + path for cross-repo findings;
- create executable contract/attack tests where possible;
- reviewer cannot modify source or certify its own findings.
