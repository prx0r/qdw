from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class AnchorReceipt:
    provider:str
    root_hex:str
    external_id:str
    anchored_at:str
    receipt:dict

class RootAnchor(Protocol):
    def anchor(self,root_hex:str)->AnchorReceipt: ...
    def verify(self,receipt:AnchorReceipt)->bool: ...

# Implement RFC3161/Rekor adapters only after local signing and ledger tests pass.
# Core operation must not depend on an external anchor service.
