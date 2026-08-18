from __future__ import annotations
import json
from pathlib import Path

class MarketplaceRegistry:
    def __init__(self,seed_path:str|Path):
        self.raw=json.loads(Path(seed_path).read_text(encoding="utf-8"))
    def get(self,marketplace_id:str)->dict:
        if marketplace_id not in self.raw:raise KeyError(marketplace_id)
        return self.raw[marketplace_id]
    def ids(self)->list[str]:
        return sorted(self.raw)
