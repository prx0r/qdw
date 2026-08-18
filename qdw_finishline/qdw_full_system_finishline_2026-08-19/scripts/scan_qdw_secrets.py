from __future__ import annotations
import argparse,json,re,sqlite3
from pathlib import Path

PATTERNS=[
 re.compile(rb"lease-token-[A-Za-z0-9_-]+"),
 re.compile(rb"QDW-LEASE"),
 re.compile(rb'"lease_token"\s*:\s*"[^"]+"'),
]
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--qdw-db",required=True)
    ap.add_argument("--evidence-root")
    a=ap.parse_args();findings=[]
    paths=[Path(a.qdw_db)]
    if a.evidence_root:
        paths.extend(p for p in Path(a.evidence_root).rglob("*") if p.is_file())
    for p in paths:
        raw=p.read_bytes()
        for pat in PATTERNS:
            if pat.search(raw):findings.append({"path":str(p),"pattern":pat.pattern.decode(errors="replace")})
    # Schema-level guard: QDW must not own a table capable of storing raw Forge lease secrets.
    con=sqlite3.connect(a.qdw_db)
    names=[x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    if "forge_leases" in names:findings.append({"path":a.qdw_db,"pattern":"retired forge_leases table still exists"})
    con.close()
    print(json.dumps(findings,indent=2))
    raise SystemExit(1 if findings else 0)
if __name__=="__main__":main()
