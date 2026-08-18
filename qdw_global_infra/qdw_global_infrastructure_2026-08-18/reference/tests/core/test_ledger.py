from qdw.core.db import Database
from qdw.core.ledger.events import Ledger

def test_chain_detects_mutation(tmp_path):
    db=Database(tmp_path/"x.db");db.migrate();l=Ledger(db)
    l.append("a","thing","1",{"x":1});l.append("b","thing","1",{"x":2})
    assert l.verify_chain()[0]
    with db.tx(immediate=True) as con:
        con.execute("UPDATE ledger_events SET payload_json=? WHERE seq=1",('{"x":999}',))
    assert not l.verify_chain()[0]

def test_epoch(tmp_path):
    db=Database(tmp_path/"x.db");db.migrate();l=Ledger(db)
    for i in range(4):l.append("x","t",str(i),{"i":i})
    e=l.seal_epoch(1,4);p=l.proof_for_seq(e["epoch_id"],3)
    assert p["tree_size"]==4 and len(p["audit_path"])>0
