from __future__ import annotations
import argparse,hashlib,json,zipfile
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument("root");ap.add_argument("--out",default="FINISHLINE_EVIDENCE.zip")
    a=ap.parse_args();root=Path(a.root);out=Path(a.out)
    files=[]
    for p in sorted(root.rglob("*")):
        if p.is_file():files.append({"path":str(p.relative_to(root)),"bytes":p.stat().st_size,"sha256":sha(p)})
    manifest={"schema":"qdw.finishline-evidence.v2","files":files}
    (root/"EVIDENCE_MANIFEST.json").write_text(json.dumps(manifest,indent=2))
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob("*")):
            if p.is_file():z.write(p,arcname=f"finishline-evidence/{p.relative_to(root)}")
    with zipfile.ZipFile(out) as z:bad=z.testzip()
    result={"path":str(out),"sha256":sha(out),"integrity":"PASS" if bad is None else "FAIL","bad":bad}
    print(json.dumps(result,indent=2))
    raise SystemExit(1 if bad else 0)
if __name__=="__main__":main()
