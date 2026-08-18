from __future__ import annotations
from .base import FactoryDefinition,FactoryPlan,FactoryPlanNode

def plan_standard_factory(d:FactoryDefinition,opportunity_id:str,public_release:bool=False)->FactoryPlan:
    nodes=[]; prev=None
    for phase in d.phases:
        key=f"phase:{phase}"
        nodes.append(FactoryPlanNode(
            key=key,kind=f"factory.{phase}",title=f"{d.name}: {phase}",
            payload={"factory_id":d.factory_id,"factory_version":d.version,
                     "opportunity_id":opportunity_id,"phase":phase},
            depends_on=(prev,) if prev else (),
            expected_cost=max(.001,d.default_budget_usd/max(1,len(d.phases))),expected_value=1.0))
        prev=key
    verify_key="phase:verify" if "verify" in d.phases else prev
    for team in d.mandatory_teams:
        nodes.append(FactoryPlanNode(
            key=f"team:{team}",kind="team.run",title=f"Global team: {team}",
            payload={"team_id":team,"factory_id":d.factory_id},
            depends_on=(verify_key,) if verify_key else (),expected_cost=.02,expected_value=.2))
    if public_release:
        for team in d.conditional_teams.get("public_release",()):
            nodes.append(FactoryPlanNode(
                key=f"team:{team}",kind="team.run",title=f"Release team: {team}",
                payload={"team_id":team,"factory_id":d.factory_id},
                depends_on=(prev,) if prev else (),expected_cost=.02,expected_value=.2))
    return FactoryPlan(d.factory_id,d.version,tuple(nodes))
