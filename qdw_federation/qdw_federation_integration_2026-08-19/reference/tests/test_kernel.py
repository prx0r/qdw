import pytest
from qdw_federation import *
from qdw_federation.adapters.forge import ForgeAdapter
from qdw_federation.fakes import FakeForgeTransport,forge_asset
from qdw_federation.store import FederationStore
from qdw_federation.router import QDWReferenceRouter
from qdw_federation.verifier import ReferenceQDWVerifier

def rcost(cost):
    return ResourceCandidate(
      FederatedRef("dell","route_candidate","o"+str(cost),digest="sha256:x"),
      "api.build",provider_id="p",model_id="m",estimated_cost_usd=cost,quality=.8)

def snapshot(status=ExternalStatus.OK,candidates=()):
    return ResourceCandidateSnapshot("dell","v1","sha256:req","now",status,tuple(candidates),"sha256:raw")

def test_external_unavailable_is_not_zero_candidates():
    k=FederationKernel(FederationStore(),QDWReferenceRouter())
    with pytest.raises(RuntimeError,match="UNAVAILABLE"):
        k.choose(capability="api.build",snapshot=snapshot(ExternalStatus.UNAVAILABLE),
                 forge_assets=(),max_cost_usd=1)

def test_unknown_cost_is_excluded_under_hard_budget():
    k=FederationKernel(FederationStore(),QDWReferenceRouter())
    s=snapshot(candidates=(rcost(None),rcost(.02)))
    c=k.choose(capability="api.build",snapshot=s,forge_assets=(),max_cost_usd=.1)
    assert c.selected_ref.object_id!="oNone"

def test_qdw_can_select_forge_and_independently_verify():
    asset=forge_asset(cost=.005,quality=.95)
    t=FakeForgeTransport([asset]);forge=ForgeAdapter(t)
    assets=forge.assets("api.build")
    k=FederationKernel(FederationStore(),QDWReferenceRouter())
    # More expensive Dell route -> Forge selected.
    c=k.choose(capability="api.build",snapshot=snapshot(candidates=(rcost(.05),)),
               forge_assets=assets,quality_floor=.7,max_cost_usd=.1)
    assert c.route_kind=="forge"
    out,cert=k.execute_forge(
      forge=forge,choice=c,capability="api.build",arguments={"task":"build"},request_id="req",
      work_ref=FederatedRef("qdw","work_node","n1",digest="sha256:n"),
      verifier=ReferenceQDWVerifier(),max_spend_usd=.1)
    assert out.status=="SUCCEEDED_UNVERIFIED"
    assert cert.status=="VERIFIED"
    assert k.store.certificates[cert.certificate_id]==cert
