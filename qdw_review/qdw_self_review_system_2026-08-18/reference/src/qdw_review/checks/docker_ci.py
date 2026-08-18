from __future__ import annotations
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

class DockerCICheck(Check):
    module_id="review.ci-reproducibility"

    def run(self,repo:Repo):
        fs=[]
        d=repo.read("Dockerfile")
        ci=repo.read(".github/workflows/ci.yml")
        if d and "RUN pip install --no-cache-dir ." in d:
            install=d.find("RUN pip install --no-cache-dir .")
            copy_src=d.find("COPY src/")
            if copy_src == -1 or install < copy_src:
                fs.append(finding(
                    rule_id="QDW-CI-001",module_id=self.module_id,severity=Severity.HIGH,
                    title="Docker installs the project before copying package source",
                    summary="The image runs `pip install .` while only pyproject.toml is present, then copies src later.",
                    invariant="Clean-image installation uses the same complete source tree that will execute.",
                    evidence=[self.evidence(repo,"Dockerfile","pip install occurs before COPY src")],
                    remediation="COPY pyproject + src (and required package metadata) before install, or build a wheel in a builder stage and install that wheel in runtime.",
                    acceptance_tests=["docker build --no-cache succeeds from a clean context.", "Container imports qdw and /health returns 200."],
                    tags=["docker","clean-build"]
                ))
        if ci and "pyright" not in ci and "[tool.pyright]" in repo.read("pyproject.toml"):
            fs.append(finding(
                rule_id="QDW-CI-002",module_id=self.module_id,severity=Severity.MEDIUM,
                title="Configured type checker is not a CI gate",
                summary="pyproject configures Pyright but CI does not execute it.",
                invariant="Declared verification ladder gates are actually executed or explicitly excluded.",
                evidence=[self.evidence(repo,".github/workflows/ci.yml","no pyright step"),self.evidence(repo,"pyproject.toml","Pyright configured")],
                remediation="Run pyright in CI and record it in verification receipts.",
                acceptance_tests=["Intentional type error makes CI fail."],
                tags=["ci","static"]
            ))
        if ci and "docker build" in ci and "docker run" not in ci:
            fs.append(finding(
                rule_id="QDW-CI-003",module_id=self.module_id,severity=Severity.MEDIUM,
                title="Docker CI proves build at most, not runtime health",
                summary="CI builds the image but never boots it or calls /health.",
                invariant="V9 Docker requires clean image boot and health smoke, not only build.",
                evidence=[self.evidence(repo,".github/workflows/ci.yml","docker build without docker run/health")],
                remediation="Start container, poll health with timeout, verify ledger/schema, then stop container.",
                acceptance_tests=["Broken CMD fails V9.", "Container returning non-200 health fails V9."],
                tags=["docker","ci","v9"]
            ))
        lockfiles=["uv.lock","poetry.lock","pdm.lock","requirements.lock"]
        if not any(repo.exists(x) for x in lockfiles):
            fs.append(finding(
                rule_id="QDW-CI-004",module_id=self.module_id,severity=Severity.LOW,
                title="No dependency lock is visible",
                summary="CI installs dependency ranges directly, reducing exact build reproducibility.",
                invariant="Release proof binds an exact dependency resolution.",
                evidence=[self.evidence(repo,"pyproject.toml","dependency ranges are declared")],
                remediation="Use a supported lock/constraints workflow and bind its hash in release certificates.",
                acceptance_tests=["Release certificate contains dependency lock hash."],
                tags=["reproducibility"]
            ))
        return self.result(fs)
