from decimal import Decimal
import pytest
from qdw.publishing.domain import DomainQuote

def _product(system):
    return system.products.create("X","x","app")

def test_human_queue_idempotent_and_strict(system):
    a=system.human.request("approval","Approve",{},idempotency_key="same")
    b=system.human.request("approval","Approve",{},idempotency_key="same")
    assert a==b
    with pytest.raises(ValueError):
        system.human.complete(a,{})
    system.human.approve(a,{"by":"human"})
    system.human.complete(a,{"done":True})

def test_domain_requires_authoritative_check_and_approval(system):
    p=_product(system)
    with pytest.raises(ValueError):
        system.domains.propose(p,DomainQuote("x.com",True,Decimal("10"),Decimal("10"),"USD",False),"cloudflare")
    did,action=system.domains.propose(p,DomainQuote("x.com",True,Decimal("10"),Decimal("10"),"USD",True),"cloudflare")
    with pytest.raises(ValueError):
        system.domains.mark_registered(did)
    system.human.approve(action,{"approved":True})
    system.domains.mark_registered(did)
