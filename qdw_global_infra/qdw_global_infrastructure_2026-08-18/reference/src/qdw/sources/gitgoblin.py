from __future__ import annotations
from typing import Protocol, Any
from dataclasses import dataclass

@dataclass(frozen=True)
class GitgoblinSignal:
    signal_id:str
    kind:str
    observed_at:str
    payload:dict[str,Any]
    evidence_refs:tuple[str,...]=()

class GitgoblinClient(Protocol):
    """Contract only. The in-progress Gitgoblin implementation remains independent."""
    def emerging_capabilities(self,*,since:str|None=None,limit:int=100)->list[GitgoblinSignal]: ...
    def people_signals(self,*,since:str|None=None,limit:int=100)->list[GitgoblinSignal]: ...
    def repo_signals(self,*,since:str|None=None,limit:int=100)->list[GitgoblinSignal]: ...
