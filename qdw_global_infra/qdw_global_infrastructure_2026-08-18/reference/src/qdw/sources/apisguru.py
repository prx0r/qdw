from __future__ import annotations
from qdw.core.core import utc_now
from .protocol import SourceResult
from .http import JSONFetcher

class APIsGuruSource:
    source_id="apis-guru"
    source_family="api_registry"
    URL="https://api.apis.guru/v2/list.json"

    def __init__(self,fetcher:JSONFetcher|None=None):self.fetcher=fetcher or JSONFetcher()

    def list_apis(self,limit:int|None=None)->SourceResult:
        try:
            data=self.fetcher.get(self.URL)
            items=[]
            for name,info in data.items():
                preferred=info.get("preferred")
                version=(info.get("versions") or {}).get(preferred,{})
                items.append({"id":name,"name":name,"preferred":preferred,
                              "info":version.get("info",{}),"swagger_url":version.get("swaggerUrl"),
                              "updated":version.get("updated")})
            if limit is not None:items=items[:limit]
            return SourceResult.success(self.source_id,self.source_family,items,utc_now())
        except Exception as e:
            return SourceResult.failure(self.source_id,self.source_family,f"{type(e).__name__}:{e}",utc_now())
