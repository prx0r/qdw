# Review Pack Builder

This directly encodes the repeated workflow used in external peer-review handoffs.

Given a persisted ReviewRun, QDW can export:

```text
qdw-review-<sha>.zip
├── README.md
├── REVIEW.json
├── REPORT.html
├── REVIEW.sarif
├── FIX_PLAN.json
├── MANIFEST.json
├── findings/
├── acceptance/
├── attacks/
├── receipts/
├── reviewer_outputs/
├── certificates/
└── docs/
```

Every exported file is hashed in MANIFEST.json and ZIP integrity is checked.

The pack is an export/read model. Canonical review truth remains in QDW's DB/ledger.
