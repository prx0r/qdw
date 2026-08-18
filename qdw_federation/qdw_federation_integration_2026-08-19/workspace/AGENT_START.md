# Agent start command sequence

From the extracted pack root:

```bash
bash scripts/clone_pinned.sh worktrees
python scripts/verify_pins.py --root worktrees
python scripts/federation_inventory.py --root worktrees > evidence-baseline-inventory.json

# Prove this pack's reference model:
python -m venv .reference-venv
.reference-venv/bin/pip install -e "reference[dev]"
.reference-venv/bin/pytest reference/tests -q
PYTHONPATH=reference/src .reference-venv/bin/python scripts/local_reference_demo.py

# Baseline real repos before patches:
bash scripts/run_all_repo_tests.sh worktrees .integration-venvs

# Preview overlays:
python scripts/apply_overlays.py --pack-root . --worktrees worktrees

# Create branches only after baseline:
bash scripts/create_integration_branch.sh worktrees

# Then review paths and apply:
python scripts/apply_overlays.py --pack-root . --worktrees worktrees --apply
```

After overlay copying, follow each `cross_repo_patches/*/INTEGRATE.md`: several existing API/composition files require
intentional edits rather than blind overwrites.
