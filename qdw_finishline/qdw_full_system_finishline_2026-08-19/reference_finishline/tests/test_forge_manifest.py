import pytest
from qdw_finishline.models import AssetManifest
from qdw_finishline.forge import ConflictError

def test_activation_does_not_change_manifest_digest(forge):
    m=forge.manifests[("api.builder","1.0.0")];before=m.manifest_digest
    forge.activate("api.builder","1.0.0","new-cert","sha256:new")
    after=forge.manifests[("api.builder","1.0.0")].manifest_digest
    assert before==after

def test_same_version_changed_manifest_rejected(forge):
    with pytest.raises(ConflictError):
        forge.register_asset(AssetManifest("api.builder","1.0.0","changed",("api.build",),.01))

def test_new_version_may_change_manifest(forge):
    x=forge.register_asset(AssetManifest("api.builder","2.0.0","changed",("api.build",),.02))
    assert x.version=="2.0.0"

def test_active_asset_exposes_same_manifest_hash(forge):
    m=forge.manifests[("api.builder","1.0.0")]
    a=forge.assets("api.build",active_only=True)[0]
    assert a["manifest_hash"]==m.manifest_digest

def test_candidate_not_returned_active_until_certificate():
    from qdw_finishline import ForgeService
    f=ForgeService();f.register_asset(AssetManifest("x","1","x",("c",),0))
    assert f.assets("c",active_only=True)==[]
