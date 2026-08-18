from __future__ import annotations
from qdw.core.core import utc_now
from .protocol import SourceResult
from .http import JSONFetcher

class MCPRegistrySource:
    source_id="mcp-registry"
    source_family="agent_registry"
    BASE="https://registry.modelcontextprotocol.io/v0.1/servers"

    def __init__(self,fetcher:JSONFetcher|None=None):self.fetcher=fetcher or JSONFetcher()

    def servers(self,*,search:str|None=None,updated_since:str|None=None,limit:int=100)->SourceResult:
        params={"limit":limit}
        if search:params["search"]=search
        if updated_since:params["updated_since"]=updated_since
        try:
            data=self.fetcher.get(self.BASE,params=params)
            items=data.get("servers",data if isinstance(data,list) else [])
            return SourceResult.success(self.source_id,self.source_family,list(items),utc_now())
        except Exception as e:
            return SourceResult.failure(self.source_id,self.source_family,f"{type(e).__name__}:{e}",utc_now())
