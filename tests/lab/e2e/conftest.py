import os,pytest
from qdw_lab.httpcheck import require_health
NAMES={"qdw":"QDW_URL","forge":"FORGE_URL","gitgoblin":"GITGOBLIN_URL","dell":"DELL_URL","forgejo":"FORGEJO_URL"}
@pytest.fixture(scope="session")
def urls():
    out={};missing=[]
    for n,e in NAMES.items():
        v=os.environ.get(e)
        if not v:missing.append(e)
        else:out[n]=v.rstrip("/")
    if missing:raise RuntimeError("missing V11 URLs: "+", ".join(missing))
    for u in out.values():require_health(u)
    return out
