import pytest
from qdw_finishline.forge import AuthorizationError,ConflictError
from qdw_finishline.models import AssetManifest

def lease(forge,ops=("invoke",)):
    return forge.create_lease(capability="api.build",asset_id="api.builder",version="1.0.0",
                              calls=2,max_spend=1,operations=ops)

def test_bad_token_cannot_invoke(forge):
    with pytest.raises(AuthorizationError):
        forge.invoke(lease_token="bad",capability="api.build",arguments={},client_request_id="r")

def test_idempotency_does_not_bypass_auth(forge):
    l=lease(forge)
    first=forge.invoke(lease_token=l["token"],capability="api.build",arguments={"x":1},client_request_id="r")
    with pytest.raises(AuthorizationError):
        forge.invoke(lease_token="bad",capability="api.build",arguments={"x":1},client_request_id="r")
    assert first.invocation_id in forge.invocations

def test_idempotency_exact_replay_returns_same(forge):
    l=lease(forge)
    a=forge.invoke(lease_token=l["token"],capability="api.build",arguments={"x":1},client_request_id="r")
    b=forge.invoke(lease_token=l["token"],capability="api.build",arguments={"x":1},client_request_id="r")
    assert a.invocation_id==b.invocation_id

def test_idempotency_changed_request_conflicts(forge):
    l=lease(forge)
    forge.invoke(lease_token=l["token"],capability="api.build",arguments={"x":1},client_request_id="r")
    with pytest.raises(ConflictError):
        forge.invoke(lease_token=l["token"],capability="api.build",arguments={"x":2},client_request_id="r")

def test_invoke_operation_required(forge):
    l=lease(forge,ops=("inspect",))
    with pytest.raises(AuthorizationError):
        forge.invoke(lease_token=l["token"],capability="api.build",arguments={},client_request_id="r")

def test_capability_must_match_lease(forge):
    l=lease(forge)
    with pytest.raises(AuthorizationError):
        forge.invoke(lease_token=l["token"],capability="other",arguments={},client_request_id="r")

def test_call_limit_enforced(forge):
    l=forge.create_lease(capability="api.build",asset_id="api.builder",version="1.0.0",
                         calls=1,max_spend=1,operations=("invoke",))
    forge.invoke(lease_token=l["token"],capability="api.build",arguments={"n":1},client_request_id="r1")
    with pytest.raises(AuthorizationError):
        forge.invoke(lease_token=l["token"],capability="api.build",arguments={"n":2},client_request_id="r2")

def test_lease_token_not_stored_plaintext(forge):
    l=lease(forge)
    stored=forge.leases[l["lease_id"]]
    assert stored.token_hash != l["token"]
    assert l["token"] not in repr(stored)
