from __future__ import annotations
import argparse,json,hashlib,zipfile
from pathlib import Path

def sha(p:Path):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--evidence-root",default=".qdw/federation")
    ap.add_argument("--pins",default="pins/REPOS.json")
    ap.add_argument("--out",default="FEDERATION_EVIDENCE.zip")
    a=ap.parse_args();root=Path(a.evidence_root);out=Path(a.out)
    files=[]
    for p in sorted(root.rglob("*")) if root.exists() else []:
        if p.is_file():files.append({"path":str(p.relative_to(root)),"bytes":p.stat().st_size,"sha256":sha(p)})
    manifest={"schema":"qdw.federation-evidence.v1",
              "pins":json.loads(Path(a.pins).read_text()),"files":files}
    tmp=root/"FEDERATION_MANIFEST.json";root.mkdir(parents=True,exist_ok=True)
    tmp.write_text(json.dumps(manifest,indent=2))
    if out.exists():out.unlink()
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob("*")):
            if p.is_file():z.write(p,arcname=f"qdw-federation-evidence/{p.relative_to(root)}")
    with zipfile.ZipFile(out) as z:
        bad=z.testzip()
    print(json.dumps({"path":str(out),"sha256":sha(out),"bytes":out.stat().st_size,
                      "integrity":"PASS" if bad is None else "FAIL","bad_file":bad},indent=2))

if __name__=="__main__":main()
