from __future__ import annotations
from pathlib import Path
import sys
from qdw.proof.plan import VerificationPlan,VerificationCommand

class ReviewerBootstrapService:
    """Certify and activate reviewer contractors using deterministic manifest/prompt fixtures."""

    def __init__(self,system,reviewer_catalog,repo_root:str|Path):
        self.system=system
        self.catalog=reviewer_catalog
        self.root=Path(repo_root).resolve()

    def bootstrap(self,*,independent_worker_id:str="reviewer-bootstrap")->list[dict]:
        out=[]
        for definition in self.catalog.definitions(include_inactive=True):
            manifest_path=self.root/"manifests/reviewers"/f"{definition['contractor_id']}.json"
            prompt_path=self.root/"prompts/reviewers"/definition["prompt_file"]

            # Global ContractorRegistry enforces same-version immutability.
            self.system.contractors.register_manifest(manifest_path)
            with self.system.db.connect() as con:
                row=con.execute("""SELECT * FROM contractor_definitions
                    WHERE contractor_id=? AND version=?""",
                    (definition["contractor_id"],definition["version"])).fetchone()
            if row["status"]=="ACTIVE":
                out.append({"contractor_id":definition["contractor_id"],"status":"ALREADY_ACTIVE"})
                continue

            plan=VerificationPlan(
                plan_id=f"reviewer-fixture:{definition['contractor_id']}",
                version=definition["version"],
                commands=(VerificationCommand(
                    "contract",
                    (
                        sys.executable,
                        "scripts/verify_reviewer_manifest.py",
                        str(manifest_path),
                        str(prompt_path),
                    ),
                    60,True,0,
                ),),
                artifacts=(str(manifest_path),str(prompt_path)),
            )
            run_id=self.system.verification.execute(
                plan,task_id=f"REVIEWER-FIXTURE:{definition['contractor_id']}",
                cwd=self.root,require_clean=True,
            )
            build=self.system.build_certificates.issue(run_id)
            cert=self.system.fixture_certificates.issue(
                subject_type="contractor",
                subject_id=definition["contractor_id"],
                subject_version=definition["version"],
                definition_hash=row["definition_hash"],
                fixture_id=definition["fixture"]["fixture_id"],
                factory_run_id=None,
                artifact_paths=[manifest_path,prompt_path],
                acceptance_plan_hash=plan.plan_hash,
                build_certificate_id=build["build_certificate_id"],
                independent_worker_id=independent_worker_id,
            )
            self.system.contractors.activate(
                definition["contractor_id"],definition["version"],
                cert["fixture_certificate_id"],
            )
            out.append({
                "contractor_id":definition["contractor_id"],
                "version":definition["version"],
                "status":"ACTIVE",
                "fixture_certificate_id":cert["fixture_certificate_id"],
            })
        self.catalog.definitions()  # forces status re-read on next selection
        return out
