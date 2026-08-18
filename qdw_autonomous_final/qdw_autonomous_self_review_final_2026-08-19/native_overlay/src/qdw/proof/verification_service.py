"""Canonical VerificationService.

All CLI/CI/build/review verification must delegate here. Compatibility wrappers may exist but
must not compute status independently.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
import glob
import json
import os
import platform
import subprocess
import sys
import time

from qdw.core import canonical_json, hash_object, new_id, utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from .plan import VerificationPlan, VerificationCommand

def _sha(b: bytes) -> str:
    return sha256(b).hexdigest()

def _git_subject(cwd: Path) -> tuple[str, bool]:
    p = subprocess.run(["git","rev-parse","HEAD"],cwd=cwd,capture_output=True,text=True,timeout=5)
    if p.returncode != 0:
        raise RuntimeError("verification requires a Git subject")
    dirty = subprocess.run(["git","status","--porcelain"],cwd=cwd,capture_output=True,text=True,timeout=5)
    return p.stdout.strip(), bool(dirty.stdout.strip())

def _env_hash(cwd: Path) -> str:
    return hash_object({
        "python": sys.version,
        "platform": platform.platform(),
        "cwd": str(cwd.resolve()),
    })

@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    verification_run_id: str
    command_id: str
    argv: tuple[str, ...]
    cwd: str
    started_at: str
    finished_at: str
    duration_ms: int
    exit_code: int
    status: str
    stdout_path: str
    stderr_path: str
    stdout_sha256: str
    stderr_sha256: str

class VerificationService:
    def __init__(self, db: Database, ledger: Ledger, runs_dir: str | Path = ".qdw/verification"):
        self.db, self.ledger = db, ledger
        self.runs_dir = Path(runs_dir)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def register_plan(self, plan: VerificationPlan) -> str:
        h = plan.plan_hash
        with self.db.tx(immediate=True) as con:
            old = con.execute(
                "SELECT plan_hash FROM verification_plans_v2 WHERE plan_id=? AND version=?",
                (plan.plan_id, plan.version),
            ).fetchone()
            if old and old["plan_hash"] != h:
                raise ValueError("verification plan version immutable; bump version")
            con.execute("""INSERT OR IGNORE INTO verification_plans_v2(
                plan_id,version,plan_hash,plan_json,status,created_at
            ) VALUES(?,?,?,?, 'ACTIVE',?)""",
            (plan.plan_id, plan.version, h, canonical_json(plan.to_dict()).decode(), utc_now()))
            self.ledger.append_in_tx(con,"verification.plan_registered","verification_plan",h,{
                "plan_id":plan.plan_id,"version":plan.version,
            })
        return h

    def execute(self, plan: VerificationPlan, *, task_id: str, cwd: str | Path = ".",
                require_clean: bool = True) -> str:
        cwdp = Path(cwd).resolve()
        subject_sha, dirty = _git_subject(cwdp)
        if require_clean and dirty:
            raise ValueError("verification subject is dirty")
        plan_hash = self.register_plan(plan)
        run_id = new_id("verify")
        run_dir = self.runs_dir / run_id
        run_dir.mkdir()
        env_hash = _env_hash(cwdp)
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO verification_runs_v2(
                verification_run_id,plan_hash,task_id,subject_git_sha,subject_dirty,cwd,
                environment_hash,status,started_at
            ) VALUES(?,?,?,?,?,?,?,'RUNNING',?)""",
            (run_id,plan_hash,task_id,subject_sha,1 if dirty else 0,str(cwdp),env_hash,utc_now()))
            self.ledger.append_in_tx(con,"verification.started","verification_run",run_id,{
                "plan_hash":plan_hash,"subject_git_sha":subject_sha,
            })

        failed = False
        for command in plan.commands:
            receipt = self._run_command(run_id, command, cwdp, run_dir)
            if command.required and receipt.status != "PASS":
                failed = True

        artifact_rows,missing_patterns = self._collect_artifacts(plan, cwdp, run_id)
        if missing_patterns:
            failed = True
        artifact_rows=sorted(artifact_rows,key=lambda x:x["path"])
        artifact_set_json=canonical_json(artifact_rows).decode()
        artifact_set_hash=hash_object(artifact_rows)

        status = "FAIL" if failed else "PASS"
        with self.db.tx(immediate=True) as con:
            con.execute("""UPDATE verification_runs_v2
                SET status=?,artifact_set_json=?,artifact_set_hash=?,finished_at=?
                WHERE verification_run_id=?""",
                (status,artifact_set_json,artifact_set_hash,utc_now(),run_id))
            self.ledger.append_in_tx(con,"verification.finished","verification_run",run_id,{
                "status":status,"artifact_count":len(artifact_rows),
                "artifact_set_hash":artifact_set_hash,
            })
        return run_id

    def _run_command(self, run_id: str, c: VerificationCommand, cwd: Path, run_dir: Path) -> Receipt:
        rid = new_id("receipt")
        started = datetime.now(UTC).isoformat().replace("+00:00","Z")
        t0 = time.monotonic()
        try:
            p = subprocess.run(list(c.argv),cwd=cwd,capture_output=True,timeout=c.timeout_seconds)
            code, stdout, stderr = p.returncode, p.stdout, p.stderr
        except subprocess.TimeoutExpired as e:
            code,stdout,stderr = 124,e.stdout or b"",e.stderr or b""
            if isinstance(stdout,str): stdout=stdout.encode()
            if isinstance(stderr,str): stderr=stderr.encode()
        duration = int((time.monotonic()-t0)*1000)
        finished = datetime.now(UTC).isoformat().replace("+00:00","Z")
        outp,errp=run_dir/f"{c.command_id}.stdout.log",run_dir/f"{c.command_id}.stderr.log"
        outp.write_bytes(stdout);errp.write_bytes(stderr)
        status = "PASS" if code == c.expected_exit_code else ("UNVERIFIED" if not c.required else "FAIL")
        receipt = Receipt(
            rid,run_id,c.command_id,c.argv,str(cwd),started,finished,duration,code,status,
            str(outp),str(errp),_sha(stdout),_sha(stderr),
        )
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO verification_receipts_v2(
                receipt_id,verification_run_id,command_id,argv_json,cwd,started_at,finished_at,
                duration_ms,exit_code,status,stdout_path,stderr_path,stdout_sha256,stderr_sha256
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rid,run_id,c.command_id,canonical_json(c.argv).decode(),str(cwd),started,finished,
             duration,code,status,str(outp),str(errp),receipt.stdout_sha256,receipt.stderr_sha256))
            self.ledger.append_in_tx(con,"verification.command","verification_receipt",rid,{
                "command_id":c.command_id,"status":status,"exit_code":code,
            })
        return receipt

    def _collect_artifacts(self, plan: VerificationPlan, cwd: Path, run_id: str) -> tuple[list[dict[str, Any]],list[str]]:
        out=[];missing=[]
        for pattern in plan.artifacts:
            matches=[]
            for raw in sorted(glob.glob(str(cwd/pattern))):
                p=Path(raw)
                if p.is_file():
                    row={"path":str(p.resolve()),"pattern":pattern,"sha256":sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size}
                    out.append(row);matches.append(row)
            if not matches:missing.append(pattern)
        return out,missing

    def run_record(self, run_id: str) -> dict[str, Any]:
        with self.db.connect() as con:
            run=con.execute("SELECT * FROM verification_runs_v2 WHERE verification_run_id=?",(run_id,)).fetchone()
            if not run: raise KeyError(run_id)
            rec=con.execute("SELECT * FROM verification_receipts_v2 WHERE verification_run_id=? ORDER BY started_at",(run_id,)).fetchall()
            plan=con.execute("SELECT * FROM verification_plans_v2 WHERE plan_hash=?",(run["plan_hash"],)).fetchone()
        return {"run":dict(run),"receipts":[dict(r) for r in rec],"plan":dict(plan)}

    def verify_evidence(self, run_id: str) -> tuple[bool, str]:
        """Verify immutable evidence without replaying commands."""
        r=self.run_record(run_id)
        run=r["run"]; plan_row=r["plan"]; plan=json.loads(plan_row["plan_json"])
        if hash_object(plan)!=run["plan_hash"] or plan_row["plan_hash"]!=run["plan_hash"]:
            return False,"plan_hash"
        if run["status"]!="PASS": return False,"run_status"
        if run["subject_dirty"]: return False,"dirty_subject"
        if not run.get("subject_git_sha") or not run.get("cwd") or not run.get("environment_hash"):
            return False,"subject_binding"

        commands={c["id"]:c for c in plan.get("commands",[])}
        required={cid for cid,c in commands.items() if c.get("required",True)}
        receipts={x["command_id"]:x for x in r["receipts"]}
        if set(receipts) < required: return False,"missing_receipt"
        if any(cid not in commands for cid in receipts): return False,"unplanned_receipt"
        for cid,c in commands.items():
            x=receipts.get(cid)
            if x is None:
                if c.get("required",True):return False,f"missing:{cid}"
                continue
            if json.loads(x["argv_json"])!=c["argv"]:return False,f"argv:{cid}"
            if x["cwd"]!=run["cwd"]:return False,f"cwd:{cid}"
            expected=int(c.get("expected_exit_code",0))
            expected_status="PASS" if x["exit_code"]==expected else ("UNVERIFIED" if not c.get("required",True) else "FAIL")
            if x["status"]!=expected_status:return False,f"status:{cid}"
            if c.get("required",True) and x["status"]!="PASS":return False,f"receipt:{cid}"
            for field,path_field in (("stdout_sha256","stdout_path"),("stderr_sha256","stderr_path")):
                p=Path(x[path_field])
                if not p.exists() or sha256(p.read_bytes()).hexdigest()!=x[field]:
                    return False,f"log_hash:{cid}"

        artifacts=json.loads(run.get("artifact_set_json") or "[]")
        if hash_object(artifacts)!=(run.get("artifact_set_hash") or hash_object([])):
            return False,"artifact_set_hash"
        expected_patterns=set(plan.get("artifacts",[]))
        found_patterns={a.get("pattern") for a in artifacts}
        if expected_patterns-found_patterns:return False,"artifact_pattern_missing"
        for art in artifacts:
            p=Path(art["path"])
            if not p.exists() or p.stat().st_size!=art["bytes"] or sha256(p.read_bytes()).hexdigest()!=art["sha256"]:
                return False,"artifact_hash"
        return True,"ok"
