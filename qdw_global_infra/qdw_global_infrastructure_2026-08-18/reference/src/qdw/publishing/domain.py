from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, Any
from qdw.core.core import canonical_json,new_id,utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.human.queue import HumanQueue

@dataclass(frozen=True)
class DomainQuote:
    fqdn:str
    registrable:bool
    registration_cost:Decimal|None=None
    renewal_cost:Decimal|None=None
    currency:str|None=None
    authoritative:bool=False
    raw:dict[str,Any]|None=None

class RegistrarAdapter(Protocol):
    def search(self,query:str,limit:int=10)->list[DomainQuote]: ...
    def check(self,domains:list[str])->list[DomainQuote]: ...

class DomainPlanner:
    """Search/check can be automated. Purchase remains an explicit HumanAction gate."""

    def __init__(self,db:Database,ledger:Ledger,human:HumanQueue):
        self.db,self.ledger,self.human=db,ledger,human

    def propose(self,product_id:str,quote:DomainQuote,registrar:str)->tuple[str,str]:
        if not quote.authoritative:
            raise ValueError("domain quote must come from authoritative check before approval")
        did=new_id("domain")
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO domains(domain_id,product_id,fqdn,registrar,status,quote_json,created_at,updated_at)
                VALUES(?,?,?,?, 'AWAITING_APPROVAL',?,?,?)""",
                (did,product_id,quote.fqdn,registrar,canonical_json({
                    "registrable":quote.registrable,
                    "registration_cost":str(quote.registration_cost) if quote.registration_cost is not None else None,
                    "renewal_cost":str(quote.renewal_cost) if quote.renewal_cost is not None else None,
                    "currency":quote.currency,
                    "authoritative":quote.authoritative,
                    "raw":quote.raw or {},
                }).decode(),utc_now(),utc_now()))
        action=self.human.request("domain_purchase_approval",f"Approve domain {quote.fqdn}",
            {"fqdn":quote.fqdn,"registrar":registrar,"registrable":quote.registrable,
             "registration_cost":str(quote.registration_cost) if quote.registration_cost is not None else None,
             "renewal_cost":str(quote.renewal_cost) if quote.renewal_cost is not None else None,
             "currency":quote.currency},
            idempotency_key=f"domain:{product_id}:{quote.fqdn}",product_id=product_id,
            estimated_cost_usd=float(quote.registration_cost) if quote.registration_cost is not None and quote.currency=="USD" else None)
        with self.db.tx(immediate=True) as con:
            con.execute("UPDATE domains SET approval_action_id=? WHERE domain_id=?",(action,did))
        self.ledger.append("domain.proposed","domain",did,{"fqdn":quote.fqdn,"approval_action_id":action})
        return did,action

    def mark_registered(self,domain_id:str,*,external_ref:str|None=None)->None:
        with self.db.tx(immediate=True) as con:
            r=con.execute("""SELECT d.approval_action_id,h.status FROM domains d
                LEFT JOIN human_actions h ON h.action_id=d.approval_action_id WHERE d.domain_id=?""",(domain_id,)).fetchone()
            if not r:raise KeyError(domain_id)
            if r["status"] not in {"APPROVED","COMPLETED"}:raise ValueError("domain purchase not approved")
            con.execute("UPDATE domains SET status='REGISTERED',updated_at=? WHERE domain_id=?",(utc_now(),domain_id))
        self.ledger.append("domain.registered","domain",domain_id,{"external_ref":external_ref})
