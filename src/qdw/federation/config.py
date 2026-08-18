from __future__ import annotations
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class FederationConfig:
    gitgoblin_url:str|None
    dell_url:str|None
    forge_url:str|None
    forge_client_key:str|None
    request_timeout_seconds:float=20.0

    @classmethod
    def from_env(cls):
        def url(name):
            v=os.environ.get(name,"").strip()
            return v.rstrip("/") if v else None
        return cls(
          url("QDW_GITGOBLIN_URL"),url("QDW_DELL_URL"),url("QDW_FORGE_URL"),
          os.environ.get("QDW_FORGE_CLIENT_KEY","").strip() or None,
          float(os.environ.get("QDW_FEDERATION_TIMEOUT_SECONDS","20"))
        )

    def configured(self):
        return {"gitgoblin":bool(self.gitgoblin_url),"dell":bool(self.dell_url),"forge":bool(self.forge_url)}
