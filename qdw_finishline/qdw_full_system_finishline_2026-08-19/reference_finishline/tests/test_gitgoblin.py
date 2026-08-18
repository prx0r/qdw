import pytest
from qdw_finishline import GitGoblinService
from qdw_finishline.runtime import FederationRuntime
from qdw_finishline import ForgeService,DellService
from qdw_finishline.models import AssetManifest

def test_export_is_versioned(gg):
    assert gg.export_qdw().schema_version=="qdw-federation-observation/1"

def test_batch_digest_stable_without_change(gg):
    assert gg.export_qdw().batch_digest==gg.export_qdw().batch_digest

def test_cursor_changes_after_observation(gg):
    a=gg.export_qdw().cursor;gg.add_observation("repo:y","momentum",.5);b=gg.export_qdw().cursor
    assert a!=b

def test_proposal_is_advisory(gg):
    p=gg.export_qdw().proposals[0]
    assert p["authority"]=="ADVISORY"

def test_runtime_ingest_is_idempotent(tmp_path,gg,forge,dell):
    r=FederationRuntime(tmp_path/"q.db",tmp_path/"r.db",gg,dell,forge)
    a=r.sync_gitgoblin();b=r.sync_gitgoblin()
    assert a["observations"]==1 and b["observations"]==0
    assert a["proposals"]==1 and b["proposals"]==0

def test_wrong_schema_rejected(tmp_path,forge,dell):
    class Bad(GitGoblinService):
        schema="bad"
    g=Bad()
    r=FederationRuntime(tmp_path/"q.db",tmp_path/"r.db",g,dell,forge)
    with pytest.raises(ValueError,match="INCOMPATIBLE_PROTOCOL"):r.sync_gitgoblin()
