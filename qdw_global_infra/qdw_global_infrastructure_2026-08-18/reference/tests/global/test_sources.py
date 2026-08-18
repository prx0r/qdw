from qdw.sources.hackernews import HackerNewsSource
from qdw.sources.yc import YCOSSCompanySource
from qdw.sources.apisguru import APIsGuruSource
from qdw.sources.mcp_registry import MCPRegistrySource

class Fake:
    def __init__(self,mapping):self.mapping=mapping
    def get(self,url,**kwargs):
        v=self.mapping[url]
        if isinstance(v,Exception):raise v
        return v

def test_hn_source_real_contract_without_network():
    base=HackerNewsSource.BASE
    f=Fake({f"{base}/askstories.json":[1],f"{base}/item/1.json":{"id":1,"title":"How do I automate invoices?"}})
    r=HackerNewsSource(f).ask()
    assert r.ok and r.items[0]["id"]==1

def test_yc_source_contract():
    f=Fake({YCOSSCompanySource.URL:[{"id":1,"name":"A"}]})
    r=YCOSSCompanySource(f).companies()
    assert r.ok and len(r.items)==1

def test_apisguru_contract():
    f=Fake({APIsGuruSource.URL:{"example.com":{"preferred":"1","versions":{"1":{"info":{"title":"E"},"swaggerUrl":"u"}}}}})
    r=APIsGuruSource(f).list_apis()
    assert r.ok and r.items[0]["id"]=="example.com"

def test_mcp_registry_contract():
    f=Fake({MCPRegistrySource.BASE:{"servers":[{"name":"x"}]}})
    r=MCPRegistrySource(f).servers()
    assert r.ok and r.items[0]["name"]=="x"

def test_source_exception_is_explicit_failure():
    f=Fake({YCOSSCompanySource.URL:RuntimeError("offline")})
    r=YCOSSCompanySource(f).companies()
    assert not r.ok and "offline" in r.error
