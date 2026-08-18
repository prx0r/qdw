from __future__ import annotations
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

class InterfaceCheck(Check):
    module_id="review.interfaces"

    def run(self,repo:Repo):
        fs=[]
        mcp_tests="\n".join(repo.read(repo.rel(p)) for p in repo.rglob("test_mcp.py"))
        if mcp_tests and "Client(" not in mcp_tests and "ClientSession(" not in mcp_tests:
            fs.append(finding(
                rule_id="QDW-IFACE-001",module_id=self.module_id,severity=Severity.MEDIUM,
                title="MCP tests appear to call Python functions rather than the protocol",
                summary="Contract tests do not appear to establish an in-process MCP client/session.",
                invariant="MCP contract proof covers initialization, tool discovery, serialization and invocation.",
                evidence=[self.evidence(repo,repo.rel(p),"MCP test file lacks protocol client") for p in repo.rglob("test_mcp.py")],
                remediation="Use the official SDK in-process client transport to list tools and invoke each required tool.",
                acceptance_tests=["Renaming/removing the registered MCP tool fails the protocol test."],
                tags=["mcp","contract"]
            ))
        api=repo.read("src/qdw/interfaces/api.py")
        if '_DB = "data/qdw.db"' in api:
            fs.append(finding(
                rule_id="QDW-IFACE-002",module_id=self.module_id,severity=Severity.LOW,
                title="API database path is hard-coded",
                summary="Runtime database selection is tied to a module constant rather than explicit configuration/composition.",
                invariant="Runtime state location is explicit and injectable.",
                evidence=[self.evidence(repo,"src/qdw/interfaces/api.py","hard-coded data/qdw.db")],
                remediation="Use a settings object/environment variable and inject QDWSystem through FastAPI lifespan/dependencies.",
                acceptance_tests=["API boots against a temporary configured DB without monkeypatching module globals."],
                tags=["api","configuration"]
            ))
        return self.result(fs)
