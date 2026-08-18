import pytest
from qdw_finishline.models import Certificate,Ref
from qdw_finishline.verifier import QDWVerifier
from qdw_finishline.forge import AuthorizationError,ConflictError

def invocation(forge):
    l=forge.create_lease(capability="api.build",asset_id="api.builder",version="1.0.0",
                         calls=1,max_spend=.1,operations=("invoke",))
    return forge.invoke(lease_token=l["token"],capability="api.build",arguments={"x":1},client_request_id="r")

def test_qdw_verifier_binds_exact_output(forge):
    inv=invocation(forge);c=QDWVerifier().verify(inv)
    assert c.subject.object_id==inv.invocation_id
    assert c.output_digest==inv.output_digest
    assert c.status=="VERIFIED"

def test_wrong_issuer_rejected(forge):
    inv=invocation(forge);c=QDWVerifier().verify(inv)
    bad=Certificate(c.certificate_id,"evil",c.subject,c.output_digest,c.policy_digest,c.status,c.certificate_digest)
    with pytest.raises(AuthorizationError):forge.bind_certificate(inv.invocation_id,bad)

def test_wrong_invocation_rejected(forge):
    inv=invocation(forge);c=QDWVerifier().verify(inv)
    bad=Certificate(c.certificate_id,c.issuer,Ref("forge","invocation","other"),c.output_digest,
                    c.policy_digest,c.status,c.certificate_digest)
    with pytest.raises(AuthorizationError):forge.bind_certificate(inv.invocation_id,bad)

def test_wrong_output_rejected(forge):
    inv=invocation(forge);c=QDWVerifier().verify(inv)
    bad=Certificate(c.certificate_id,c.issuer,c.subject,"sha256:wrong",c.policy_digest,c.status,c.certificate_digest)
    with pytest.raises(AuthorizationError):forge.bind_certificate(inv.invocation_id,bad)

def test_same_certificate_replay_is_idempotent(forge):
    inv=invocation(forge);c=QDWVerifier().verify(inv)
    forge.bind_certificate(inv.invocation_id,c);before=dict(forge.profiles[("api.builder","1.0.0","api.build")])
    forge.bind_certificate(inv.invocation_id,c);after=forge.profiles[("api.builder","1.0.0","api.build")]
    assert before==after

def test_certificate_cannot_replay_to_different_subject(forge):
    inv=invocation(forge);c=QDWVerifier().verify(inv);forge.bind_certificate(inv.invocation_id,c)
    l=forge.create_lease(capability="api.build",asset_id="api.builder",version="1.0.0",
                         calls=1,max_spend=.1,operations=("invoke",))
    inv2=forge.invoke(lease_token=l["token"],capability="api.build",arguments={"x":2},client_request_id="r2")
    with pytest.raises((AuthorizationError,ConflictError)):forge.bind_certificate(inv2.invocation_id,c)
