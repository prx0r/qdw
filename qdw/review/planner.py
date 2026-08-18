from __future__ import annotations
from hashlib import sha256
import json
from .reviewers import ReviewerCatalog

def _h(x)->str:
    return sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

class ReviewPlanner:
    def __init__(self,graphs,reviewers:ReviewerCatalog):
        self.graphs=graphs
        self.reviewers=reviewers

    def plan_semantic_graph(self,*,review_run_id:str,round_id:str,changed_paths:tuple[str,...],
                            profile:str,policy,subject_sha:str)->tuple[str,list[dict]]:
        selected=[
            d for d in self.reviewers.select(changed_paths,profile)
            if d["contractor_id"]!="review.release-certifier"
        ]
        required=set(policy.required_reviewers)
        by_id={
            d["contractor_id"]:d for d in self.reviewers.definitions()
            if d["contractor_id"]!="review.release-certifier"
        }
        for rid in required:
            if rid in by_id and by_id[rid] not in selected:
                selected.append(by_id[rid])

        gid=self.graphs.create_graph()
        nodes=[]
        for d in sorted(selected,key=lambda x:x["contractor_id"]):
            nid=self.graphs.add_node(
                gid,"reviewer",f"Review: {d['contractor_id']}",
                {
                    "review_run_id":review_run_id,
                    "review_round_id":round_id,
                    "subject_git_sha":subject_sha,
                    "reviewer_id":d["contractor_id"],
                    "reviewer_version":d["version"],
                    "reviewer_definition_hash":d["definition_hash"],
                    "changed_paths":changed_paths,
                },
                expected_cost=d.get("default_budget_usd"),
                quality_floor=d.get("quality_floor",0.75),
                idempotency_key=f"{round_id}:{d['contractor_id']}:{d['version']}",
            )
            nodes.append({"node_id":nid,"definition":d})

        # Meta-review depends on other semantic reviewers.
        meta=next((x for x in nodes if x["definition"]["contractor_id"]=="review.claim-consistency"),None)
        if meta:
            for n in nodes:
                if n is not meta:
                    self.graphs.add_edge(gid,n["node_id"],meta["node_id"])

        if hasattr(self.graphs,"freeze"):
            self.graphs.freeze(gid)
        else:
            raise RuntimeError("review requires hardened WorkGraphStore.freeze()")
        return gid,nodes
