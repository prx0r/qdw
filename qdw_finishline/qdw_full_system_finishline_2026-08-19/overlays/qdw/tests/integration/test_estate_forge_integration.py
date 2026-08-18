from qdw.federation.contracts import CapabilityExecutionRequest,FederatedRef,VerificationCertificateRef
from qdw.federation.forge_adapter import ForgeExecutionAdapter

class FakeNetworkForge:
    def __init__(self,substitute=False):
        self.substitute=substitute;self.bound=None
    def lease(self,body):
        return {"token":"test-token","lease":{"lease_id":"l1"}}
    def invoke(self,body):
        asset="other" if self.substitute else "asset"
        return {
          "invocation_id":"i1","asset_id":asset,"version":"1","status":"SUCCEEDED_UNVERIFIED",
          "output":{"ok":True},"output_hash":"sha256:output","cost_usd":.01,
          "route_decision":{"policy":"pinned"}}
    def bind_certificate(self,invocation_id,body):
        self.bound=(invocation_id,body);return {"status":"VERIFIED"}

def request():
    return CapabilityExecutionRequest(
      request_id="req",capability="fixture.echo",
      selected_asset=FederatedRef("forge","capability_asset","asset",version="1",digest="sha256:a"),
      arguments={"x":1},max_spend_usd=.1,qdw_work_node_id="n1",qdw_route_digest="sha256:r")

def test_real_adapter_pins_asset_version():
    a=ForgeExecutionAdapter(FakeNetworkForge())
    x=a.execute(request())
    assert x.selected_asset.object_id=="asset"
    assert x.status=="SUCCEEDED_UNVERIFIED"

def test_asset_substitution_is_rejected():
    import pytest
    a=ForgeExecutionAdapter(FakeNetworkForge(substitute=True))
    with pytest.raises(RuntimeError,match="FORGE_ASSET_SUBSTITUTION"):a.execute(request())

def test_certificate_wire_contains_reference_not_legacy_boolean():
    f=FakeNetworkForge();a=ForgeExecutionAdapter(f)
    c=VerificationCertificateRef(
      "qdw","c","sha256:c",FederatedRef("forge","invocation","i1"),
      "sha256:output","sha256:p","VERIFIED")
    a.bind_certificate_reference("i1",c)
    payload=f.bound[1]
    assert "certificate" in payload
    assert "pass"+"ed" not in payload
