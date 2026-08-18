from __future__ import annotations
from qdw.core.core import utc_now
from .protocol import SourceResult
from .http import JSONFetcher

class YCOSSCompanySource:
    """Consumes the yc-oss public derived API. Treat as third-party public-source adapter."""
    source_id="yc-oss"
    source_family="startup_directory"
    URL="https://yc-oss.github.io/api/companies/all.json"

    def __init__(self,fetcher:JSONFetcher|None=None):self.fetcher=fetcher or JSONFetcher()

    def companies(self,limit:int|None=None)->SourceResult:
        try:
            data=self.fetcher.get(self.URL)
            items=list(data if isinstance(data,list) else data.get("companies",[]))
            if limit is not None:items=items[:limit]
            return SourceResult.success(self.source_id,self.source_family,items,utc_now())
        except Exception as e:
            return SourceResult.failure(self.source_id,self.source_family,f"{type(e).__name__}:{e}",utc_now())
