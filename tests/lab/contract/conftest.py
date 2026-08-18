import os,pytest
from qdw_lab.httpcheck import require_health

NAMES={"qdw":"QDW_URL","forge":"FORGE_URL","gitgoblin":"GITGOBLIN_URL","dell":"DELL_URL","forgejo":"FORGEJO_URL"}

@pytest.fixture(scope="session")
def urls():
    out={}
    missing=[]
    for name,var in NAMES.items():
        v=os.environ.get(var)
        if not v:missing.append(var)
        else:out[name]=v.rstrip("/")
    if missing:raise RuntimeError("required federation lab URLs missing: "+", ".join(missing))
    for name,url in out.items():require_health(url)
    return out
