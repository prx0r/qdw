# QDW Self-Review / Contractor Audit System

Target reviewed head: `prx0r/qdw@c1ab1e46c41587c85253278ed5e012b0f757a551`

This pack turns the repeated external peer-review loop into a callable QDW subsystem.

It contains:

- a standalone `qdw-review` CLI that can audit any local QDW checkout;
- deterministic static reviewers;
- process-backed dynamic verification receipts;
- an adversarial attack catalog;
- reusable reviewer / red-team contractor manifests;
- QDW integration schema and service overlays;
- deliberately failing regression tests for the current QDW trust-boundary bugs;
- an interactive HTML report for the reviewed head;
- a machine-readable current review;
- a release review policy and certificate model;
- implementation tasks and frozen acceptance criteria.

The core rule is:

```text
AGENT OPINION != VERIFIED FINDING
FILE EXISTS != FEATURE WORKS
ID EXISTS != EVIDENCE IS BOUND TO THE RIGHT OBJECT
PASS BOOLEAN != CERTIFICATE
SOURCE FAILURE != ZERO RESULTS
UNKNOWN != ZERO
STATE CHANGE WITHOUT PROVENANCE != ATOMIC EVENT
```

## Immediate use

From this extracted pack:

```bash
python -m pip install -e "reference[dev]"
qdw-review scan /path/to/qdw --profile quick --out .qdw/review
qdw-review scan /path/to/qdw --profile full --out .qdw/review
qdw-review report .qdw/review/latest.json --html .qdw/review/report.html
qdw-review gate .qdw/review/latest.json --policy policies/release.json
```

For QDW integration, read:

1. `agent/MASTER_IMPLEMENTATION_PROMPT.md`
2. `docs/00_SYSTEM_ARCHITECTURE.md`
3. `docs/01_CURRENT_QDW_PEER_REVIEW.md`
4. `docs/02_REVIEWER_CONTRACTORS.md`
5. `docs/03_ADVERSARIAL_TESTING.md`
6. `integration/INTEGRATION_MAP.md`

Do not blindly copy the reference package into `qdw.core`. The reference package is a standalone
review tool. The `integration/` and `overlay/` directories show how to make it a QDW-native subsystem.
