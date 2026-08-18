"""State and semantic provenance must commit together."""

import pytest

from qdw.core.db import Database
from qdw.core.graph.store import WorkGraphStore
from qdw.core.ledger.events import Ledger


def test_graph_creation_rolls_back_if_event_write_fails(tmp_path, monkeypatch):
    d = Database(tmp_path / "qdw.db"); d.migrate()
    ledger = Ledger(d); store = WorkGraphStore(d, ledger)

    def boom(*args, **kwargs):
        raise RuntimeError("injected ledger failure")
    monkeypatch.setattr(ledger, "append_in_tx", boom)

    with pytest.raises(RuntimeError):
        store.create_graph(graph_id="graph_atomic")

    with d.connect() as con:
        assert con.execute("SELECT 1 FROM work_graphs WHERE graph_id='graph_atomic'").fetchone() is None
