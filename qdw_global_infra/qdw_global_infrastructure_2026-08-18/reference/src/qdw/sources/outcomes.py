from __future__ import annotations
from typing import Protocol, Any

class ProductAnalyticsAdapter(Protocol):
    def product_metrics(self,external_product_key:str,start:str,end:str)->dict[str,Any]: ...

class OutcomeIngestor:
    """Provider-neutral adapter boundary for PostHog/Plausible/etc."""
    def __init__(self,products):self.products=products
    def ingest(self,product_id:str,metrics:dict[str,Any],*,source:str,occurred_at:str|None=None)->list[str]:
        ids=[]
        for name,value in metrics.items():
            if isinstance(value,(int,float)):
                ids.append(self.products.outcome(product_id,name,value=float(value),source=source,occurred_at=occurred_at))
            else:
                ids.append(self.products.outcome(product_id,name,text_value=str(value),source=source,occurred_at=occurred_at))
        return ids
