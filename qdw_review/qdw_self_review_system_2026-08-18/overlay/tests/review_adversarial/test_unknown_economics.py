"""UNKNOWN economics may not silently become optimistic constants."""

from qdw.core.db import Database
from qdw.core.graph.store import WorkGraphStore
from qdw.core.ledger.events import Ledger

def test_unknown_cost_does_not_beat_known_positive_economics(tmp_path):
    d=Database(tmp_path/"qdw.db");d.migrate();g=WorkGraphStore(d,Ledger(d))
    gid=g.create_graph()
    known=g.add_node(gid,"task","known",{},expected_value=.6,expected_cost=.1)
    unknown=g.add_node(gid,"task","unknown",{},expected_value=1.0,expected_cost=None)
    g.refresh_ready(gid)
    claimed=g.claim_ready("reviewer",graph_id=gid)
    assert claimed["node_id"] == known, (
        "UNKNOWN cost must be blocked/information-gathering/explicit-prior; it cannot become zero"
    )
