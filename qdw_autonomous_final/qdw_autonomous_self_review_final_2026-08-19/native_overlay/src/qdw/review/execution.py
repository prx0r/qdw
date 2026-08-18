"""Execute review and fix nodes through existing WorkGraph + Executor semantics."""
from __future__ import annotations
from qdw.executors.protocol import ExecutionRequest
from .worker import SemanticReviewWorker

class ReviewWorkGraphExecutor:
    def __init__(self,*,graphs,store,reviewers,executor,workspace:str,
                 worker_id:str="qdw-autoreview"):
        self.graphs,self.store,self.reviewers=graphs,store,reviewers
        self.executor=executor
        self.semantic=SemanticReviewWorker(executor)
        self.workspace=workspace
        self.worker_id=worker_id

    def execute_graph(self,graph_id:str)->None:
        while True:
            self.graphs.refresh_ready(graph_id)
            node=self.graphs.claim_ready(self.worker_id,graph_id=graph_id)
            if not node:
                break
            kind=node["kind"];payload=node["payload"]
            self.graphs.start(node["node_id"],self.worker_id)
            try:
                if kind=="reviewer":
                    self._review(node,payload)
                elif kind=="review_fix":
                    self._fix(node,payload)
                else:
                    raise ValueError(f"unsupported review graph node kind {kind}")
            except Exception as exc:
                self.graphs.fail(node["node_id"],{"error":str(exc)},retryable=False)
                raise

    def _review(self,node,payload):
        definition=next(d for d in self.reviewers.definitions()
            if d["contractor_id"]==payload["reviewer_id"]
            and d["version"]==payload["reviewer_version"])
        mid=self.store.create_module_run(
            payload["review_round_id"],definition["contractor_id"],definition["version"],
            definition["definition_hash"],node["node_id"],
            worker_id=self.worker_id,executor_id=getattr(self.executor,"executor_id",None),
        )
        result=self.semantic.run(
            review_run_id=payload["review_run_id"],module_run_id=mid,definition=definition,
            prompt=self.reviewers.prompt(definition),subject_sha=payload["subject_git_sha"],
            workspace=self.workspace,changed_paths=tuple(payload.get("changed_paths",())),
        )
        self.graphs.verifying(node["node_id"])
        fids=self.store.ingest_result(
            payload["review_run_id"],payload["review_round_id"],mid,result,payload["subject_git_sha"]
        )
        if result.status!="ok":
            self.graphs.fail(node["node_id"],{"review_status":result.status},retryable=False)
            return
        self.graphs.complete(node["node_id"],{"module_run_id":mid,"finding_ids":fids})

    def _fix(self,node,payload):
        prompt=(
            "Repair the listed QDW peer-review findings in the current workspace. "
            "Do not modify or weaken frozen acceptance specs. "
            "Run the exact acceptance checks exposed in payload. "
            "Make bounded production-code changes, run focused regressions, then commit the changes. "
            "Return changed files, commit SHA and command evidence. "
            "Do not declare the findings FIXED; independent review does that."
        )
        request=ExecutionRequest(
            run_id=payload["review_run_id"],node_id=node["node_id"],task_kind="review_fix",
            prompt=prompt,payload=payload,workspace=self.workspace,
            timeout_seconds=1800,budget_usd=None,required_capabilities=("code_edit","tests","git"),
        )
        result=self.executor.execute(request)
        self.graphs.verifying(node["node_id"])
        if not result.ok:
            self.graphs.fail(node["node_id"],{"status":result.status,"stderr":result.stderr},retryable=True)
            return
        self.graphs.complete(node["node_id"],{
            "status":result.status,
            "final":result.final,
            "exit_code":result.exit_code,
        })
