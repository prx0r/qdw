#!/usr/bin/env python3
"""Deterministic reviewer-contractor fixture verifier."""
from __future__ import annotations
import argparse,json
from pathlib import Path

REQUIRED={
    "contractor_id","version","team","specialization","description","inputs","outputs","gates",
    "path_patterns","prompt_file","independence","fixture"
}

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("manifest")
    p.add_argument("prompt")
    args=p.parse_args()
    manifest=json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    missing=REQUIRED-set(manifest)
    if missing:raise SystemExit(f"missing fields: {sorted(missing)}")
    if not manifest["contractor_id"].startswith("review."):
        raise SystemExit("reviewer contractor_id must start review.")
    if manifest["team"]!="peer_review":
        raise SystemExit("reviewer team must be peer_review")
    if manifest["independence"].get("may_self_certify") is not False:
        raise SystemExit("reviewer may_self_certify must be false")
    prompt=Path(args.prompt).read_text(encoding="utf-8")
    for phrase in ("Output contract","acceptance","evidence"):
        if phrase.lower() not in prompt.lower():
            raise SystemExit(f"prompt missing required contract phrase: {phrase}")
    if manifest["fixture"].get("kind")!="reviewer_contract":
        raise SystemExit("reviewer fixture kind invalid")
    print(json.dumps({
        "status":"PASS","contractor_id":manifest["contractor_id"],
        "version":manifest["version"],"prompt_bytes":len(prompt.encode()),
    }))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
