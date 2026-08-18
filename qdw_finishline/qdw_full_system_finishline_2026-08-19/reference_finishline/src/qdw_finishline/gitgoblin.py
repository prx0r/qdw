from __future__ import annotations
from .models import ObservationBatch
from .hashing import digest

class GitGoblinService:
    schema="qdw-federation-observation/1"
    def __init__(self):
        self.observations=[];self.proposals=[];self.revision="gitgoblin-fixture-r1";self.cursor=0
    def add_observation(self,entity_key,metric,value,evidence="fixture"):
        self.cursor+=1
        self.observations.append({
          "external_ref":{"system":"gitgoblin","object_type":"observation",
                          "object_id":f"obs_{self.cursor}"},
          "entity_key":entity_key,"metric":metric,"value":value,
          "evidence_digest":digest({"evidence":evidence}),"source_family":"fixture","confidence":1.0})
    def add_proposal(self,proposal_id,problem,decision="BUILD"):
        self.proposals.append({
          "external_ref":{"system":"gitgoblin","object_type":"opportunity_proposal","object_id":proposal_id},
          "problem":problem,"external_decision":decision,"authority":"ADVISORY"})
    def export_qdw(self):
        return ObservationBatch(self.schema,"gitgoblin",str(self.cursor),self.revision,
                                tuple(self.observations),tuple(self.proposals))
