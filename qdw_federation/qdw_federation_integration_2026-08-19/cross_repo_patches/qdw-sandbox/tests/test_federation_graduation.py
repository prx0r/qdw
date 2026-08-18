import pytest
from sandbox.estate.federation.graduation import assert_not_production_authority

@pytest.mark.parametrize("name",["EstateRouter","EstateVerificationService","EstateScheduler"])
def test_duplicate_estate_authority_disabled(name):
    with pytest.raises(PermissionError):assert_not_production_authority(name)
