from pathlib import Path
import pytest

@pytest.fixture
def broken_repo(tmp_path: Path) -> Path:
    def w(rel: str, text: str) -> None:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')

    # Split proof authority + post-hoc certificate requirements.
    w('src/qdw/core/verification/runner.py', 'class VerificationRunner: pass\n')
    w('src/qdw/proof/runner.py', 'class VerificationRunner: pass\n')
    w('scripts/build_certificate.py', '''\nreceipts = runner.load_receipts()\nrequired_cmds = list({tuple(r.argv) for r in receipts})\nacceptance_spec_hash="ci_pipeline"\n''')
    w('src/qdw/proof/certificate.py', '''\n# negative tests still fail\ndef verify():\n    if receipt.exit_code == 0:\n        raise ValueError("negative test passed when it should have failed")\n''')
    w('.github/workflows/ci.yml', '''\n- run: pytest tests/unit -q\n- run: pytest tests/adversarial -q\n- run: python scripts/build_certificate.py\n- run: docker build -t qdw:test .\n- run: python -c "assert 1 in v; assert 2 in v"\n''')

    # Weak trust boundaries.
    w('src/qdw/factories/registry.py', '''\ndef activate(factory_id, version, fixture_certificate_id):\n    cert = con.execute("SELECT * FROM gate_results WHERE gate_result_id=?", (fixture_certificate_id,)).fetchone()\n    cert_version = detail.get("factory_version")\n    if cert_version and cert_version != version: raise ValueError()\n''')
    w('src/qdw/contractors/registry.py', '''\ndef activate(contractor_id, version, fixture_certificate_id):\n    cert = con.execute("SELECT * FROM gate_results WHERE gate_result_id=?", (fixture_certificate_id,)).fetchone()\n    cert_version = detail.get("contractor_version")\n    if cert_version and cert_version != version: raise ValueError()\n''')
    w('src/qdw/products/registry.py', '''\ndef release(product_id, certificate_id):\n    cert = con.execute("SELECT * FROM gate_results WHERE gate_result_id=?", (certificate_id,)).fetchone()\n''')

    # Split state/event transactions and cycle validation after commit.
    w('src/qdw/core/graph/store.py', '''\nclass WorkGraphStore:\n    def create_graph(self):\n        with self.db.tx(immediate=True) as con:\n            con.execute("INSERT")\n            self.ledger.append_in_tx(con, "graph.created", "graph", "g", {})\n    def add_node(self):\n        with self.db.tx(immediate=True) as con: con.execute("INSERT")\n        self.ledger.append("node.created", "node", "n", {})\n    def add_edge(self):\n        with self.db.tx(immediate=True) as con:\n            con.execute("INSERT OR IGNORE INTO work_edges VALUES(1)")\n        cycles = self.validate_dag("g")\n        if cycles: raise ValueError(cycles[0])\n        self.ledger.append("edge.created", "graph", "g", {})\n    def refresh_ready(self):\n        with self.db.tx(immediate=True) as con: con.execute("UPDATE")\n        self.ledger.append("node.ready", "node", "n", {})\n    def reclaim_stale(self):\n        with self.db.tx(immediate=True) as con: con.execute("UPDATE")\n        self.ledger.append("node.reclaimed", "node", "n", {})\n    def claim_ready(self):\n        with self.db.tx(immediate=True) as con: con.execute("UPDATE")\n        self.ledger.append("node.claimed", "node", "n", {})\n    def start(self):\n        with self.db.tx(immediate=True) as con: con.execute("UPDATE")\n        self.ledger.append("node.started", "node", "n", {})\n    def verifying(self):\n        with self.db.tx(immediate=True) as con: con.execute("UPDATE")\n        self.ledger.append("node.verifying", "node", "n", {})\n    def complete(self):\n        with self.db.tx(immediate=True) as con: con.execute("UPDATE")\n        self.ledger.append("node.succeeded", "node", "n", {})\n    def fail(self):\n        with self.db.tx(immediate=True) as con: con.execute("UPDATE")\n        self.ledger.append("node.failed", "node", "n", {})\n''')

    # Migration gaps.
    w('src/qdw/core/migrations.py', '''\ndef migrate():\n    con.executescript(sql)\n    con.execute("INSERT INTO schema_versions(version, applied_at, content_hash) VALUES(?,?,?)")\n    if row["content_hash"] and row["content_hash"] != content_hash: raise ValueError()\n''')
    w('migrations/0004_foreign_keys.sql', '''\nINSERT OR IGNORE INTO products_new SELECT * FROM products;\nDROP TABLE IF EXISTS products;\nALTER TABLE products_new RENAME TO products;\n''')

    # HotSwap loss/race.
    w('src/qdw/hotswap/types.py', '''\nclass Route:\n    route_id: str\n    model_id: str\n    provider_id: str\n    endpoint_id: str\n    account_id: str\n    prior_success: float\n    prior_confidence: float\n    breaker_open: bool\n    quota_pressure: float\n    evidence_ids: list[str]\n''')
    w('src/qdw/hotswap/persistent.py', '''\ndef get(self, cell_id, route):\n    self._upsert(cell_id, route.route_id, posterior)\ndef _upsert(self, cell_id, route_id, posterior):\n    con.execute("ON CONFLICT(route_id) DO UPDATE SET alpha=excluded.alpha")\ndef save_route(self, route):\n    route_id = route.route_id; model_id=route.model_id; provider_id=route.provider_id\n''')
    w('src/qdw/system.py', '''\nclass QDWSystem:\n    def register_route(self, route):\n        self.routes.append(route)\n''')

    # Simulated factory fixture and incomplete E2E.
    w('tests/factories/test_api_factory.py', '''\ndef test_fixture():\n    gate = lambda ctx: (ctx.get("ok") is True, {})\n    result = gate({"ok": True})\n    assert result[0]\n''')
    w('tests/integration/test_e2e.py', '''\ndef test_e2e():\n    assert WorldStore and ProductRegistry\n''')

    # Review package deliberately absent.
    return tmp_path
