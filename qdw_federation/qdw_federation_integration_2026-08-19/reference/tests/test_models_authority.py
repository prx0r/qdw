import pytest
from qdw_federation.models import *
from qdw_federation.authority import authorize,assert_authority

def ref(system="dell",typ="offer",oid="x",version=None):
    return FederatedRef(system,typ,oid,version=version,digest="sha256:x")

def test_federated_ref_requires_identity():
    with pytest.raises(ValueError): FederatedRef("","offer","x")

def test_decision_advisory_cannot_claim_authority():
    with pytest.raises(ValueError):
        DecisionAdvisory("dell","a","m",None,(),(),"sha256:s","now",AuthorityKind.CERTIFICATE)

def test_execution_request_requires_pinned_forge_version():
    with pytest.raises(ValueError):
        CapabilityExecutionRequest("r","api.build",FederatedRef("forge","capability_asset","a"),{},1)
    with pytest.raises(ValueError):
        CapabilityExecutionRequest("r","api.build",FederatedRef("dell","offer","a",version="1"),{},1)

def test_execution_result_cannot_self_verify():
    with pytest.raises(ValueError):
        InvocationOutcome(ref("forge","invocation","i"),ref("forge","capability_asset","a","1"),
                          "VERIFIED",{}, "sha256:o", .1, None)

def test_authority_matrix():
    assert authorize("qdw","workgraph").allowed
    assert authorize("dell","provider_model_truth").allowed
    assert authorize("forge","capability_asset_registry").allowed
    assert not authorize("dell","final_execution_route").allowed
    assert not authorize("sandbox","qdw_verification").allowed
    with pytest.raises(PermissionError): assert_authority("gitgoblin","portfolio_decision")

def test_unknown_cost_remains_none():
    c=ResourceCandidate(ref(),"inference",estimated_cost_usd=None)
    assert c.estimated_cost_usd is None
