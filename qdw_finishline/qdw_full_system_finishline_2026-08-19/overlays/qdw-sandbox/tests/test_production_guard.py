import pytest
from sandbox.estate.production_guard import assert_incubator_only

@pytest.mark.parametrize("name",[
  "EstateRouter","EstateVerificationService","EstateScheduler","EstateWorkGraphAuthority"])
def test_duplicate_production_authorities_are_blocked(name):
    with pytest.raises(PermissionError):assert_incubator_only(name)

def test_pure_context_components_may_be_donors():
    assert assert_incubator_only("ContextPackAssembler")
