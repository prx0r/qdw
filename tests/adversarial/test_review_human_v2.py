import pytest
from qdw.human.queue import HumanQueue

def test_stale_approval_payload_rejected(db,ledger):
    q=HumanQueue(db,ledger)
    aid=q.request("domain_purchase","Buy x",{"domain":"x.com","price":10},
                  idempotency_key="domain:x")
    q.approve(aid,"owner",{})
    changed=q.action_payload(
        action_type="domain_purchase",title="Buy x",
        instructions={"domain":"x.com","price":50}
    )
    with pytest.raises(ValueError,match="APPROVAL_PAYLOAD_MISMATCH"):
        q.require_approved(aid,expected_payload=changed)

def test_missing_actor_rejected(db,ledger):
    q=HumanQueue(db,ledger)
    aid=q.request("release","Release",{},idempotency_key="r1")
    with pytest.raises((TypeError,ValueError)):
        q.approve(aid,"")
