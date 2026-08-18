from __future__ import annotations
from datetime import UTC,datetime
from typing import Any
from gitgoblin.hashing import sha256_json
from gitgoblin.models import FrontierSignal,Opportunity

SCHEMA="qdw-federation-observation/1"

def signal_observations(signal:FrontierSignal)->list[dict[str,Any]]:
    evidence_hash=sha256_json(signal.model_dump(mode="json"))
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
    return [{
      "external_ref":{
        "system":"gitgoblin","object_type":"observation",
        "object_id":f"{signal.signal_id}:{metric}",
        "digest":"sha256:"+sha256_json({"signal":signal.signal_id,"metric":metric,"value":value}),
      },
      "entity_key":signal.target_id,"metric":metric,"value":value,
      "unit":"score" if isinstance(value,float) else "count",
      "observed_at":signal.detected_at.isoformat(),
      "source_family":"frontier_attention",
      "evidence_digest":"sha256:"+evidence_hash,
      "confidence":signal.confidence,
      "dimensions":{"sector":signal.sector,"quality":quality,"evidence_ids":signal.evidence_ids},
    } for metric,value in fields.items()]

def opportunity_proposal(opp:Opportunity)->dict[str,Any]:
    raw=opp.model_dump(mode="json")
    return {
      "external_ref":{"system":"gitgoblin","object_type":"opportunity_proposal",
                      "object_id":opp.opportunity_id,"digest":"sha256:"+sha256_json(raw)},
      "problem":opp.problem,"sector":opp.sector,"primitive":opp.primitive,
      "evidence_ids":opp.evidence_ids,"scorecard":opp.scorecard,
      "external_decision":opp.decision,"solution_hypotheses":opp.solution_hypotheses,
      "authority":"ADVISORY",
    }

def build_export(store,sector:str|None=None,cursor:str|None=None)->dict[str,Any]:
    signals=store.signals(sector,1000);opps=store.opportunities(sector,1000)
    observations=[x for s in signals for x in signal_observations(s)]
    payload={
      "schema_version":SCHEMA,"source_system":"gitgoblin",
      "cursor":cursor or datetime.now(UTC).isoformat(),
      "generated_at":datetime.now(UTC).isoformat(),
      "observations":observations,
      "opportunity_proposals":[opportunity_proposal(o) for o in opps],
    }
    payload["batch_digest"]="sha256:"+sha256_json(payload)
    return payload
