from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json,tempfile,zipfile
from .report import html,sarif

def _write_json(path:Path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2),encoding="utf-8")

class ReviewPackBuilder:
    def build(self,*,report:dict,fix_tasks:list[dict],acceptance_specs:list[dict],
              attack_results:list[dict],reviewer_outputs:list[dict],receipts:list[dict],
              certificates:list[dict],output_zip:str|Path)->dict:
        output_zip=Path(output_zip)
        with tempfile.TemporaryDirectory(prefix="qdw-review-pack-") as td:
            sha=((report.get("subject") or {}).get("git_sha") or report.get("git_sha") or "unknown")[:12]
            pack_root=Path(td)/("qdw-review-"+sha)
            pack_root.mkdir()
            _write_json(pack_root/"REVIEW.json",report)
            (pack_root/"REPORT.html").write_text(html(report),encoding="utf-8")
            _write_json(pack_root/"REVIEW.sarif",sarif(report))
            _write_json(pack_root/"FIX_PLAN.json",fix_tasks)
            _write_json(pack_root/"attacks/ATTACK_RESULTS.json",attack_results)
            _write_json(pack_root/"reviewer_outputs/OUTPUTS.json",reviewer_outputs)
            _write_json(pack_root/"receipts/RECEIPTS.json",receipts)
            _write_json(pack_root/"certificates/CERTIFICATES.json",certificates)
            for i,spec in enumerate(acceptance_specs,1):
                _write_json(pack_root/f"acceptance/{i:03d}.json",spec)
            for module in report.get("modules",[]):
                for finding in module.get("findings",[]):
                    name=finding.get("finding_id",finding["rule_id"])
                    _write_json(pack_root/f"findings/{name}.json",finding)
            (pack_root/"README.md").write_text(
                "# QDW Review Pack\\n\\nGenerated from canonical QDW review state.\\n",
                encoding="utf-8",
            )
            files=[]
            for p in sorted(pack_root.rglob("*")):
                if p.is_file() and p.name!="MANIFEST.json":
                    b=p.read_bytes()
                    files.append({"path":str(p.relative_to(pack_root)),"bytes":len(b),"sha256":sha256(b).hexdigest()})
            _write_json(pack_root/"MANIFEST.json",{"schema":"qdw.review-pack.v1","files":files})
            output_zip.parent.mkdir(parents=True,exist_ok=True)
            if output_zip.exists():output_zip.unlink()
            with zipfile.ZipFile(output_zip,"w",zipfile.ZIP_DEFLATED) as z:
                for p in sorted(pack_root.rglob("*")):
                    if p.is_file():
                        z.write(p,arcname=f"{pack_root.name}/{p.relative_to(pack_root)}")
            with zipfile.ZipFile(output_zip) as z:
                bad=z.testzip()
            return {
                "path":str(output_zip),
                "sha256":sha256(output_zip.read_bytes()).hexdigest(),
                "bytes":output_zip.stat().st_size,
                "files":len(files)+1,
                "integrity":"PASS" if bad is None else "FAIL",
                "bad_file":bad,
            }
