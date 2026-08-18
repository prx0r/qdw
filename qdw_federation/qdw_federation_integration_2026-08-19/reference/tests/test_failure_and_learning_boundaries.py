from qdw_federation.models import *
from qdw_federation.router import QDWReferenceRouter

def test_forge_profile_is_a_feature_not_qdw_posterior():
    a=CapabilityAssetView(
      FederatedRef("forge","capability_asset","x",version="1",digest="sha256:x"),
      "x",("coding",),True,"ACTIVE",pricing_per_call=.01,posterior_mean=.9,sample_count=100)
    c=QDWReferenceRouter().choose(capability="coding",dell_candidates=(),forge_assets=(a,),
                                  quality_floor=.7,max_cost_usd=.1)
    # Reference decision can use profile as hint, but does not expose/copy alpha/beta QDW state.
    assert c.quality_hint==.9
    assert not hasattr(c,"alpha") and not hasattr(c,"beta")

def test_stale_and_unavailable_are_distinct_from_ok_empty():
    assert len({ExternalStatus.STALE,ExternalStatus.UNAVAILABLE,ExternalStatus.OK_EMPTY})==3
