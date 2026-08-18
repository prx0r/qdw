import pytest
from qdw_federation.adapters.forge import ForgeAdapter
from qdw_federation.fakes import FakeForgeTransport,forge_asset
from qdw_federation.models import *
from qdw_federation.verifier import ReferenceQDWVerifier

def selected():
    a=forge_asset()
    return FederatedRef("forge","capability_asset",a["asset_id"],version=a["version"],digest=a["manifest_hash"])

def request():
    return CapabilityExecutionRequest("req1","api.build",selected(),{"x":1},max_spend_usd=.1)

def test_forge_lease_is_pinned_and_invocation_unverified():
    t=FakeForgeTransport([forge_asset()])
    a=ForgeAdapter(t)
    out=a.execute(request())
    lease=list(t.leases.values())[0]
    assert lease["asset_id"]=="worker.api" and lease["version"]=="1.0.0"
    assert out.status=="SUCCEEDED_UNVERIFIED"

def test_forge_asset_substitution_is_detected():
    t=FakeForgeTransport([forge_asset(),forge_asset("evil","9.9.9")],substitute=True)
    with pytest.raises(RuntimeError,match="FORGE_ASSET_SUBSTITUTION"):
        ForgeAdapter(t).execute(request())

def test_certificate_binding_has_no_pass_boolean():
    t=FakeForgeTransport([forge_asset()])
    a=ForgeAdapter(t);out=a.execute(request())
    cert=ReferenceQDWVerifier().verify_invocation(
        out,FederatedRef("qdw","work_node","node1",digest="sha256:n"))
    a.bind_certificate(out,cert)
    body=t.bound_certificates[out.invocation_ref.object_id]
    assert "passed" not in body
    assert body["certificate"]["status"]=="VERIFIED"

def test_wrong_invocation_certificate_rejected():
    t=FakeForgeTransport([forge_asset()])
    a=ForgeAdapter(t);out=a.execute(request())
    cert=VerificationCertificateRef(
        "qdw","c","sha256:c",
        FederatedRef("forge","invocation","different",digest="sha256:i"),
        out.output_digest,"sha256:p","VERIFIED")
    with pytest.raises(ValueError,match="invocation mismatch"):a.bind_certificate(out,cert)

def test_wrong_output_digest_certificate_rejected():
    t=FakeForgeTransport([forge_asset()])
    a=ForgeAdapter(t);out=a.execute(request())
    cert=VerificationCertificateRef(
        "qdw","c","sha256:c",out.invocation_ref,"sha256:wrong","sha256:p","VERIFIED")
    with pytest.raises(ValueError,match="output digest mismatch"):a.bind_certificate(out,cert)


def test_forge_discovery_preserves_certificate_and_version():
    t=FakeForgeTransport([forge_asset()])
    xs=ForgeAdapter(t).assets("api.build")
    assert len(xs)==1
    assert xs[0].external_ref.version=="1.0.0"
    assert xs[0].certified and xs[0].status=="ACTIVE"
