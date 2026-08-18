from qdw_finishline import ForgeService
from qdw_finishline.forgejo import ForgejoService,ForgejoSync,Repo

def repo(n):
    return Repo("org",f"r{n}","main",f"sha{n}",{
      "assets":[{"asset_id":f"a{n}","version":"1","name":f"a{n}",
                 "capabilities":["c"],"pricing":{"per_call":0.01}}]})

def test_sync_reads_manifest_at_commit_not_branch():
    fj=ForgejoService([repo(1)]);f=ForgeService();s=ForgejoSync(fj,f);s.sync_org("org")
    assert fj.read_log==[("org","r1","sha1")]

def test_sync_paginates_past_fifty():
    repos=[repo(i) for i in range(61)];fj=ForgejoService(repos);f=ForgeService()
    x=ForgejoSync(fj,f).sync_org("org",limit=10)
    assert x["repos"]==61 and x["assets"]==61

def test_provenance_contains_repo_commit_manifest_digest():
    fj=ForgejoService([repo(1)]);f=ForgeService();ForgejoSync(fj,f).sync_org("org")
    m=f.manifests[("a1","1")]
    assert m.source_repo=="forgejo://org/r1" and m.source_commit=="sha1"
    assert m.source_manifest_digest.startswith("sha256:")

def test_repeat_sync_is_idempotent():
    fj=ForgejoService([repo(1)]);f=ForgeService();s=ForgejoSync(fj,f)
    s.sync_org("org");s.sync_org("org")
    assert len(f.manifests)==1

def test_changed_same_version_manifest_is_rejected():
    fj=ForgejoService([repo(1)]);f=ForgeService();s=ForgejoSync(fj,f);s.sync_org("org")
    fj.repos=[Repo("org","r1","main","sha2",{
      "assets":[{"asset_id":"a1","version":"1","name":"changed","capabilities":["c"],"pricing":{"per_call":.01}}]})]
    import pytest
    with pytest.raises(Exception):s.sync_org("org")
