#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json,shutil,zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/(ROOT.name+'.zip')
summary=json.loads((ROOT/'VALIDATION_SUMMARY.json').read_text())
if summary.get('status')!='PACK_VALIDATED':raise SystemExit('refuse ZIP: pack validation is not PASS')
for p in list(ROOT.rglob('__pycache__'))+list(ROOT.rglob('.pytest_cache')):
    if p.is_dir():shutil.rmtree(p,ignore_errors=True)
entries=[]
for p in sorted(ROOT.rglob('*')):
    if p.is_file() and p.name!='MANIFEST.json':
        b=p.read_bytes();entries.append({'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':sha256(b).hexdigest()})
manifest={
 'schema':'qdw.final-autonomous-review-pack.v1',
 'reviewed_qdw_head':summary['reviewed_qdw_head'],
 'validation_status':summary['status'],
 'peer_review_counts':summary['peer_review_counts'],
 'file_count_excluding_manifest':len(entries),
 'files':entries,
}
(ROOT/'MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
if OUT.exists():OUT.unlink()
with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(ROOT.rglob('*')):
        if p.is_file():z.write(p,arcname=f'{ROOT.name}/{p.relative_to(ROOT)}')
with zipfile.ZipFile(OUT) as z:
    bad=z.testzip();count=len(z.namelist())
if bad:raise SystemExit(f'ZIP CRC failed: {bad}')
result={'path':str(OUT),'bytes':OUT.stat().st_size,'sha256':sha256(OUT.read_bytes()).hexdigest(),
        'zip_entries':count,'zip_integrity':'PASS','manifest_files':len(entries)+1}
(ROOT/'validation/FINAL_ZIP.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
# Rebuild one last time to include FINAL_ZIP.json in the user artifact; the external digest is recomputed afterward by caller.
with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(ROOT.rglob('*')):
        if p.is_file():z.write(p,arcname=f'{ROOT.name}/{p.relative_to(ROOT)}')
with zipfile.ZipFile(OUT) as z:
    bad=z.testzip();count=len(z.namelist())
result={'path':str(OUT),'bytes':OUT.stat().st_size,'sha256':sha256(OUT.read_bytes()).hexdigest(),
        'zip_entries':count,'zip_integrity':'PASS' if bad is None else 'FAIL','bad_file':bad}
print(json.dumps(result,indent=2))
