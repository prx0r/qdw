# Install and dogfood the final review layer

The pack now includes `scripts/apply_native_overlay.py`.

Dry-run against the exact reviewed head:

```bash
python scripts/apply_native_overlay.py /path/to/qdw
```

Apply locally:

```bash
python scripts/apply_native_overlay.py /path/to/qdw --apply
```

The installer never pushes or merges and refuses an unexpected starting SHA by default. If QDW has moved,
peer-review the new head before blindly applying an old overlay.

After applying:

1. retain the starting SHA and frozen failing receipts;
2. run the implementation task graph;
3. run `qdw review self --profile release` on the final clean SHA;
4. export the review with the native `NativeReviewPackBuilder`;
5. require `verify_pack()` to pass before handoff/release.

This is how the external ZIP workflow becomes an internal QDW capability: the ZIP is only an export of canonical
review state, not the source of truth.
