from pathlib import Path
import pytest

@pytest.fixture
def broken_repo(tmp_path:Path)->Path:
    def w(rel,text):
        p=tmp_path/rel
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(text)
        return p

    w("scripts/build_certificate.py", """
builder.issue(task_id='x', acceptance_spec_hash="manual_review",
              required_commands=[], required_negative_tests=[], artifact_paths=[])
""")
    w("src/qdw/proof/certificate.py", """
def verify_certificate(path):
    stored_hash='x'; recomputed='x'
    if stored_hash != recomputed:return False,'hash'
    if {'status':'PROVEN'}.get('status')!='PROVEN':return False,'status'
    return True,'ok'
""")
    w("src/qdw/factories/registry.py", """
def activate(self,factory_id,version,fixture_certificate_id):
    cert=con.execute("SELECT * FROM gate_results WHERE gate_result_id=?", (fixture_certificate_id,)).fetchone()
    if not cert['passed']: raise ValueError()
""")
    w("src/qdw/products/registry.py", """
class ProductRegistry:
 def create(self,name,slug,product_type,*,idea_id=None,factory_id: str | None = None,factory_version=None,build_run_id: str | None = None):pass
 def release(self,product_id,certificate_id):
  con.execute("UPDATE products SET status='RELEASED',certificate_id=?",(certificate_id,))
 def outcome(self,metric, *, source: str = "manual"):pass
""")
    w("src/qdw/contractors/registry.py", """
def register_manifest():
 con.execute("ON CONFLICT(contractor_id,version) DO UPDATE SET definition_hash=excluded.definition_hash")
def activate(self,contractor_id,version):
 con.execute("UPDATE contractor_definitions SET status='ACTIVE'")
""")
    w("src/qdw/core/graph/store.py", """
class X:
 def validate_dag(self): pass
 def claim_ready(self):
  candidate=Candidate(expected_value=nv if nv is not None else 1.0,
                      expected_cost=nc if nc is not None else 0.0)
 def fail(self):
  state='RETRY_WAIT' if n["attempt_count"] <= n["max_retries"] else 'FAILED'
 def reclaim_stale(self):
  if r["attempt_count"] >= r["max_retries"]: pass
 def create_graph(self):
  with self.db.tx(immediate=True) as con:
   con.execute('INSERT')
  self.ledger.append('graph.created','graph','g',{})
""")
    w("src/qdw/hotswap/persistent.py", """
def update(self,cell_id,route_id,success):
 with self.db.connect() as con:
  row=con.execute("SELECT alpha, beta FROM route_posteriors").fetchone()
 self._upsert(cell_id,route_id,nxt)
def mean_and_lower(self): pass
def _upsert(self,*x):
 with self.db.tx(immediate=True) as con:pass
""")
    w("src/qdw/hotswap/quota.py", "class QuotaLedger:\n def __init__(self): self.used={}\n")
    w("src/qdw/system.py", '"""the single composition root; all registries and services are injected here."""\nfrom x import Route\nclass QDWSystem:\n def __init__(self):\n  self.routes: list[Route] = []\n')
    for rel,cls in [
        ("src/qdw/world/store.py","WorldStore"),
        ("src/qdw/intelligence/painfinder.py","PainFinder"),
        ("src/qdw/intelligence/stack_oracle.py","StackOracle"),
        ("src/qdw/intelligence/opportunities.py","OpportunityStore"),
        ("src/qdw/watch/service.py","WatchService"),
        ("src/qdw/catalog/service.py","GlobalCatalog"),
    ]:
        w(rel,f"class {cls}: pass\n")
    w("src/qdw/ideas/service.py", """
class IdeaService: pass
def bury():
 con.execute("ON CONFLICT(idea_id) DO UPDATE SET reason_code=excluded.reason_code")
""")
    w("src/qdw/ideas/pipeline.py","def review(self, *, passed: bool): return 'PASS' if passed else 'REJECT'\n")
    w("src/qdw/human/queue.py","class HumanQueue: pass\ndef _transition(self, action_id, new_status, payload=None): pass\n")
    w("src/qdw/core/migrations.py", '"""transactional migration runner"""\ndef migrate(db):\n sql="x"\n with db.connect() as con:\n  con.executescript(sql)\n  con.execute("INSERT OR IGNORE INTO schema_versions(version, applied_at) VALUES(?,?)")\n')
    w("src/qdw/core/db.py","def migrate(self, migrations_dir=None):\n from qdw.core.migrations import migrate_all\n migrate_all(self)\n")
    w("migrations/0002_global.sql", """
CREATE TABLE IF NOT EXISTS products (
 product_id TEXT PRIMARY KEY,
 idea_id TEXT,
 build_run_id TEXT,
 certificate_id TEXT
);
CREATE TABLE IF NOT EXISTS outcome_events (
 outcome_event_id TEXT PRIMARY KEY,
 product_id TEXT NOT NULL,
 metric TEXT NOT NULL
);
""")
    w("Dockerfile","FROM python:3.13-slim\nCOPY pyproject.toml .\nRUN pip install --no-cache-dir .\nCOPY src/ src/\n")
    w("pyproject.toml","[tool.pyright]\npythonVersion='3.12'\n")
    w(".github/workflows/ci.yml","run: ruff check src/qdw tests\nrun: docker build -t qdw:test .\n")
    w("tests/integration/test_e2e.py","from qdw.products.registry import ProductRegistry\n\ndef test_e2e():\n    assert ProductRegistry\n")
    w("tests/contract/test_mcp.py","def test_tool():\n    assert callable(tool)\n")
    return tmp_path
