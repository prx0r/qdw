from __future__ import annotations
from datetime import UTC,datetime
import os
from gitgoblin.hashing import sha256_json

SCHEMA="qdw-federation-observation/1"

def _sha(x):
    h=sha256_json(x)
    return h if str(h).startswith("sha256:") else "sha256:"+str(h)

def _signal_observations(signal):
    raw=signal.model_dump(mode="json")
    evidence_digest=_sha(raw)
    quality={
      "confidence":signal.confidence,
      "expert_count":signal.expert_count,
      "independent_cluster_count":signal.independent_cluster_count,
      "evidence_count":len(signal.evidence_ids),
    }
    fields={
      "technical_alpha":signal.technical_alpha,
      "novelty":signal.novelty,
      "momentum":signal.momentum,
      "expert_count":signal.expert_count,
      "independent_cluster_count":signal.independent_cluster_count,
    }
    out=[]
    for metric,value in fields.items():
        oid=f"{signal.signal_id}:{metric}"
        payload={
          "external_ref":{"system":"gitgoblin","object_type":"observation","object_id":oid},
          "entity_key":signal.target_id,"metric":metric,"value":value,
          "unit":"score" if isinstance(value,float) else "count",
          "observed_at":signal.detected_at.isoformat(),
          "source_family":"frontier_attention",
          "evidence_digest":evidence_digest,
          "confidence":signal.confidence,
          "dimensions":{"sector":signal.sector,"quality":quality,"evidence_ids":list(signal.evidence_ids)},
        }
        payload["external_ref"]["digest"]=_sha(payload)
        out.append(payload)
    return out

def _proposal(opp):
    raw=opp.model_dump(mode="json")
    return {
      "external_ref":{"system":"gitgoblin","object_type":"opportunity_proposal",
                      "object_id":opp.opportunity_id,"digest":_sha(raw)},
      "problem":opp.problem,"sector":opp.sector,"primitive":opp.primitive,
      "evidence_ids":list(opp.evidence_ids),"scorecard":opp.scorecard,
      "external_decision":opp.decision,
      "solution_hypotheses":list(opp.solution_hypotheses),
      "authority":"ADVISORY",
    }

def build_export(store,*,sector=None,cursor=None,limit=1000):
    signals=store.signals(sector,limit)
    if cursor:
        signals=[s for s in signals if s.detected_at.isoformat()>cursor]
    opportunities=store.opportunities(sector,limit)
    observations=[o for s in signals for o in _signal_observations(s)]
    max_cursor=max((s.detected_at.isoformat() for s in signals),default=cursor or "")
    payload={
      "schema_version":SCHEMA,
      "source_system":"gitgoblin",
      "source_revision":os.environ.get("GITGOBLIN_BUILD_SHA","unknown"),
      "cursor":max_cursor,
      "generated_at":datetime.now(UTC).isoformat(),
      "observations":observations,
      "opportunity_proposals":[_proposal(o) for o in opportunities],
    }
    # Hash excludes generation timestamp so repeated unchanged export is stable.
    payload["batch_digest"]=_sha({
      "schema_version":payload["schema_version"],"source_system":payload["source_system"],
      "source_revision":payload["source_revision"],"cursor":payload["cursor"],
      "observations":payload["observations"],"opportunity_proposals":payload["opportunity_proposals"],
    })
    return payload
