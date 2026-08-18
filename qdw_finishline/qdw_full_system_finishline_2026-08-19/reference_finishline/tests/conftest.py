import pytest
from qdw_finishline import ForgeService,GitGoblinService,DellService
from qdw_finishline.models import AssetManifest
from qdw_finishline.forgejo import ForgejoService,Repo

@pytest.fixture
def forge():
    f=ForgeService()
    m=AssetManifest("api.builder","1.0.0","API Builder",("api.build",),0.01,
                    source_repo="forgejo://qdw/api-builder",source_commit="abc",
                    source_manifest_digest="sha256:manifest")
    f.register_asset(m);f.activate(m.asset_id,m.version,"asset-cert","sha256:asset-cert")
    return f

@pytest.fixture
def gg():
    g=GitGoblinService();g.add_observation("repo:x","momentum",0.9);g.add_proposal("p1","build x")
    return g

@pytest.fixture
def dell():
    return DellService([{
      "offer_id":"inference-1","provider_id":"p","model_id":"m",
      "input_per_m":10.0,"output_per_m":10.0,"free":False,"score":0.8,"quality":0.8
    }])
