from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path

@dataclass(frozen=True)
class TeamDefinition:
    team_id:str
    version:str
    name:str
    outputs:tuple[str,...]
    gates:tuple[str,...]
    default_budget_usd:float

def load_team(path:str|Path)->TeamDefinition:
    m=json.loads(Path(path).read_text(encoding="utf-8"))
    return TeamDefinition(m["team_id"],m["version"],m["name"],tuple(m["outputs"]),
                          tuple(m["gates"]),float(m.get("default_budget_usd",0)))
