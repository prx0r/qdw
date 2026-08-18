from qdw_federation.adapters.sandbox import SandboxEstateAdapter

def test_estate_contract_maps_without_becoming_authority():
    a=SandboxEstateAdapter()
    x=a.capability_request({
      "request_id":"r","capability":"coding","objective":"fix","verification_policy":"tests",
      "constraints":{"max_cost_usd":1,"network":"none","external_writes":False},
      "quality_floor":.8
    })
    assert x["capability"]=="coding"
    assert x["budget"]["max_cost_usd"]==1
    assert x["external_ref"].system=="sandbox"

def test_competing_estate_authorities_retired():
    a=SandboxEstateAdapter()
    assert not a.production_authority_allowed("EstateRouter")
    assert not a.production_authority_allowed("EstateVerificationService")
    assert not a.production_authority_allowed("EstateScheduler")
    assert a.production_authority_allowed("ContextPackAssembler")
