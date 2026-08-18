from qdw_lab.httpcheck import get_json

def test_stub_has_more_than_fifty_repos(urls):
    a=get_json(urls["forgejo"],"/api/v1/orgs/qdw/repos",params={"page":1,"limit":50})
    b=get_json(urls["forgejo"],"/api/v1/orgs/qdw/repos",params={"page":2,"limit":50})
    assert len(a)==50 and len(b)>0

def test_manifest_requires_immutable_commit(urls):
    import httpx
    repos=get_json(urls["forgejo"],"/api/v1/orgs/qdw/repos",params={"page":1,"limit":1})
    name=repos[0]["name"]
    branch=httpx.get(urls["forgejo"]+f"/api/v1/repos/qdw/{name}/contents/qdw.yaml",params={"ref":"main"},timeout=10)
    assert branch.status_code==409
