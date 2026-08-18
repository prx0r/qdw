from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any
import json
from qdw.core import canonical_json,new_id,utc_now

@dataclass(frozen=True)
class AttackDefinition:
    attack_id:str
    version:str
    category:str
    description:str
    argv:tuple[str,...]
    expected_reason_code:str|None=None
    required:bool=True
    timeout_seconds:int=300

class AttackCatalog:
    def __init__(self,path:str|Path):
        self.path=Path(path)

    def all(self)->list[AttackDefinition]:
        d=json.loads(self.path.read_text(encoding="utf-8"))
        out=[]
        for x in d:
            out.append(AttackDefinition(
                x["attack_id"],x.get("version","1.0.0"),x["category"],x["description"],
                tuple(x["argv"]),x.get("expected_reason_code"),bool(x.get("required",True)),
                int(x.get("timeout_seconds",300)),
            ))
        return out

    def select(self,ids:tuple[str,...])->list[AttackDefinition]:
        by={x.attack_id:x for x in self.all()}
        missing=[x for x in ids if x not in by]
        if missing:raise ValueError(f"unknown attacks: {missing}")
        return [by[x] for x in ids]

class AttackRunner:
    """Execute attack tests through the canonical VerificationService.

    The command itself is expected to PASS. The test is responsible for proving the malicious action
    was rejected for the expected reason and optionally writing an AttackResult JSON artifact.
    """
    def __init__(self,db,ledger,verification):
        self.db,self.ledger,self.verification=db,ledger,verification

    def run(self,round_id:str,attack:AttackDefinition,*,cwd:str|Path,subject_sha:str)->dict[str,Any]:
        from qdw.proof.plan import VerificationPlan,VerificationCommand
        plan=VerificationPlan(
            plan_id=f"attack:{attack.attack_id}",
            version=attack.version,
            commands=(VerificationCommand(
                "attack",attack.argv,attack.timeout_seconds,True,0
            ),),
        )
        run_id=self.verification.execute(plan,task_id=f"attack:{attack.attack_id}",cwd=cwd,require_clean=False)
        record=self.verification.run_record(run_id)
        receipt=record["receipts"][0]
        status="PASS" if receipt["status"]=="PASS" else "FAIL"
        detail={
            "attack_id":attack.attack_id,
            "subject_git_sha":subject_sha,
            "description":attack.description,
            "verification_run_id":run_id,
            "receipt_id":receipt["receipt_id"],
            "command_status":receipt["status"],
            "reason_evidence":"asserted by frozen attack test; runner does not fabricate actual reason",
        }
        arid=new_id("attackresult")
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO review_attack_results(
                attack_result_id,review_round_id,attack_id,attack_version,status,
                expected_reason_code,actual_reason_code,verification_run_id,receipt_id,detail_json,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (arid,round_id,attack.attack_id,attack.version,status,attack.expected_reason_code,
             None,run_id,receipt["receipt_id"],
             canonical_json(detail).decode(),utc_now()))
            self.ledger.append_in_tx(con,"review.attack","review_attack",arid,{
                "attack_id":attack.attack_id,"status":status,
            })
        return {"attack_result_id":arid,**detail,"status":status,"expected_reason_code":attack.expected_reason_code}
