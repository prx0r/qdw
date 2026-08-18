# Finding Lifecycle

Stable fingerprint:

```text
rule ID
+ reviewer module
+ affected canonical path/object
```

Lifecycle:

```text
OPEN
  -> ACKNOWLEDGED
  -> FIXED
  -> REGRESSION (if fingerprint reappears)

OPEN -> SUPPRESSED
OPEN -> WONT_FIX
```

Suppressions:
- never delete finding history;
- require actor + reason;
- expire by default;
- cannot suppress CRITICAL under release policy;
- bind to policy/subject where appropriate.

A fix closes only after its acceptance test runs on the new subject SHA.
