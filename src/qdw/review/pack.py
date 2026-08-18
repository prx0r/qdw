from __future__ import annotations
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import json,shutil,tempfile,zipfile
from qdw.core import new_id,utc_now

def _j(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,default=str),encoding="utf-8")

def _render_shape(report):
    groups=defaultdict(list)
    for finding in report["findings"]:
        f={
            "finding_id":finding["finding_id"],
            "rule_id":finding["rule_id"],
            "module_id":finding["module_id"],
            "severity":finding["severity"],
            "title":finding["title"],
            "summary":finding["summary"],
            "invariant":finding["invariant_text"],
            "remediation":finding["remediation"],
            "evidence":[],
            "acceptance_tests":[],
            "status":finding["status"],
        }
        groups[finding["module_id"]].append(f)
    modules=[
        {
            "module_id":mid,"version":"persisted","status":"FAIL" if any(
                x["status"] in {"OPEN","REGRESSION"} and x["severity"] in {"CRITICAL","HIGH"} for x in fs
            ) else "PASS",
            "findings":fs,"notes":[],
        }
        for mid,fs in sorted(groups.items())
    ]
    counts={s:sum(1 for f in report["findings"] if f["severity"]==s)
            for s in ("CRITICAL","HIGH","MEDIUM","LOW","INFO")}
    return {
        "schema_version":"qdw.review.export.v2",
        "subject":{"git_sha":report["review_run"]["subject_git_sha"],
                   "dirty":bool(report["review_run"]["subject_dirty"]),
                   "repo_path":"canonical-review-export"},
        "profile":report["review_run"]["profile"],
        "generated_at":utc_now(),
        "counts":counts,"modules":modules,
        "attacks":report["attacks"],"receipts":[],
    }

class NativeReviewPackBuilder:
    """Export a complete interactive handoff from canonical review state."""

    def __init__(self,store,report_service):
        self.store,self.report_service=store,report_service

    def export(self,review_run_id:str,output_zip:str|Path)->dict:
        from .render import html,sarif

        report=self.report_service.build(review_run_id)
        with self.store.db.connect() as con:
            evidence=[dict(r) for r in con.execute("""SELECT e.* FROM review_evidence e
                JOIN review_findings f ON f.finding_id=e.finding_id
                WHERE f.review_run_id=? ORDER BY f.created_at,e.created_at""",
                (review_run_id,)).fetchall()]
            specs=[dict(r) for r in con.execute("""SELECT DISTINCT a.* FROM review_acceptance_specs a
                JOIN review_finding_acceptance fa ON fa.acceptance_spec_id=a.acceptance_spec_id
                JOIN review_findings f ON f.finding_id=fa.finding_id
                WHERE f.review_run_id=? ORDER BY a.frozen_at""",(review_run_id,)).fetchall()]
            acceptance_state=[dict(r) for r in con.execute("""SELECT fa.* FROM review_finding_acceptance fa
                JOIN review_findings f ON f.finding_id=fa.finding_id
                WHERE f.review_run_id=?""",(review_run_id,)).fetchall()]
            certs=[dict(r) for r in con.execute(
                "SELECT * FROM review_certificates WHERE review_run_id=?",(review_run_id,)
            ).fetchall()]
            run=con.execute("SELECT * FROM review_runs WHERE review_run_id=?",(review_run_id,)).fetchone()
            fix_nodes=[]
            if run and run["fix_graph_id"]:
                fix_nodes=[dict(r) for r in con.execute("""SELECT node_id,kind,title,state,payload_json,result_json
                    FROM work_nodes WHERE graph_id=? ORDER BY created_at""",(run["fix_graph_id"],)).fetchall()]

            verification_ids={x["verification_run_id"] for x in report["attacks"] if x.get("verification_run_id")}
            verification_ids.update(x["verification_run_id"] for x in acceptance_state if x.get("verification_run_id"))
            verification_runs=[];receipts=[]
            for vrid in sorted(verification_ids):
                vr=con.execute("SELECT * FROM verification_runs_v2 WHERE verification_run_id=?",(vrid,)).fetchone()
                if vr:
                    verification_runs.append(dict(vr))
                    receipts.extend(dict(r) for r in con.execute("""SELECT * FROM verification_receipts_v2
                        WHERE verification_run_id=? ORDER BY started_at""",(vrid,)).fetchall())

        evidence_by_finding=defaultdict(list)
        for e in evidence:evidence_by_finding[e["finding_id"]].append(e)
        for finding in report["findings"]:
            finding["evidence"]=evidence_by_finding.get(finding["finding_id"],[])

        renderable=_render_shape(report)
        for module in renderable["modules"]:
            for finding in module["findings"]:
                finding["evidence"]=evidence_by_finding.get(finding["finding_id"],[])

        output_zip=Path(output_zip)
        with tempfile.TemporaryDirectory(prefix="qdw-native-review-") as td:
            subject=report["review_run"]["subject_git_sha"]
            pack_root=Path(td)/f"qdw-review-{subject[:12]}"
            pack_root.mkdir()

            _j(pack_root/"REVIEW.json",report)
            _j(pack_root/"RENDERABLE_REVIEW.json",renderable)
            (pack_root/"REPORT.html").write_text(html(renderable),encoding="utf-8")
            _j(pack_root/"REVIEW.sarif",sarif(renderable))
            _j(pack_root/"EVIDENCE.json",evidence)
            _j(pack_root/"ACCEPTANCE.json",{"specs":specs,"state":acceptance_state})
            _j(pack_root/"FIX_PLAN.json",fix_nodes)
            _j(pack_root/"ATTACK_RESULTS.json",report["attacks"])
            _j(pack_root/"REVIEWER_RUNS.json",report["modules"])
            _j(pack_root/"VERIFICATION_RUNS.json",verification_runs)
            _j(pack_root/"RECEIPTS.json",receipts)
            _j(pack_root/"CERTIFICATES.json",certs)

            for finding in report["findings"]:
                _j(pack_root/f"findings/{finding['finding_id']}.json",finding)
            for spec in specs:
                _j(pack_root/f"acceptance/{spec['acceptance_spec_id']}.json",spec)

            # Copy actual process logs when they still exist.
            for receipt in receipts:
                for kind,path_key in (("stdout","stdout_path"),("stderr","stderr_path")):
                    src=Path(receipt[path_key])
                    if src.exists():
                        dst=pack_root/f"logs/{receipt['receipt_id']}.{kind}.log"
                        dst.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copyfile(src,dst)

            summary=(
                f"# QDW autonomous peer review\\n\\n"
                f"- Review run: `{review_run_id}`\\n"
                f"- Subject: `{subject}`\\n"
                f"- Status: `{report['review_run']['status']}`\\n"
                f"- Findings: `{len(report['findings'])}`\\n"
                f"- Attack results: `{len(report['attacks'])}`\\n"
                f"- Verification receipts: `{len(receipts)}`\\n\\n"
                "Open `REPORT.html` for the interactive view. `REVIEW.json` is the canonical export.\\n"
            )
            (pack_root/"README.md").write_text(summary,encoding="utf-8")

            files=[]
            for path in sorted(pack_root.rglob("*")):
                if path.is_file() and path.name!="MANIFEST.json":
                    data=path.read_bytes()
                    files.append({
                        "path":str(path.relative_to(pack_root)),
                        "bytes":len(data),
                        "sha256":sha256(data).hexdigest(),
                    })
            manifest={
                "schema":"qdw.review-pack.v2",
                "review_run_id":review_run_id,
                "subject_git_sha":subject,
                "generated_at":utc_now(),
                "file_count":len(files),
                "files":files,
            }
            _j(pack_root/"MANIFEST.json",manifest)

            output_zip.parent.mkdir(parents=True,exist_ok=True)
            if output_zip.exists():output_zip.unlink()
            with zipfile.ZipFile(output_zip,"w",zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(pack_root.rglob("*")):
                    if path.is_file():
                        archive.write(path,arcname=f"{pack_root.name}/{path.relative_to(pack_root)}")
            with zipfile.ZipFile(output_zip) as archive:
                bad=archive.testzip()

        digest=sha256(output_zip.read_bytes()).hexdigest()
        with self.store.db.tx(immediate=True) as con:
            export_id=new_id("reviewexport")
            con.execute("""INSERT INTO review_pack_exports(
                export_id,review_run_id,artifact_path,artifact_sha256,bytes,file_count,created_at
            ) VALUES(?,?,?,?,?,?,?)""",
            (export_id,review_run_id,str(output_zip),digest,output_zip.stat().st_size,len(files)+1,utc_now()))
            self.store.ledger.append_in_tx(con,"review.pack_exported","review_export",export_id,{
                "review_run_id":review_run_id,"sha256":digest,
            })
        return {
            "export_id":export_id,"path":str(output_zip),"sha256":digest,
            "bytes":output_zip.stat().st_size,"files":len(files)+1,
            "integrity":"PASS" if bad is None else "FAIL",
        }

def verify_pack(path:str|Path)->tuple[bool,str]:
    path=Path(path)
    with zipfile.ZipFile(path) as archive:
        bad=archive.testzip()
        if bad:return False,f"zip_crc:{bad}"
        names=archive.namelist()
        roots={name.split("/",1)[0] for name in names if "/" in name}
        if len(roots)!=1:return False,"root"
        root=next(iter(roots))
        manifest_name=f"{root}/MANIFEST.json"
        if manifest_name not in names:return False,"manifest_missing"
        manifest=json.loads(archive.read(manifest_name))
        for entry in manifest.get("files",[]):
            member=f"{root}/{entry['path']}"
            if member not in names:return False,f"member_missing:{entry['path']}"
            data=archive.read(member)
            if sha256(data).hexdigest()!=entry["sha256"]:
                return False,f"member_hash:{entry['path']}"
            if len(data)!=entry["bytes"]:
                return False,f"member_size:{entry['path']}"
    return True,"ok"
