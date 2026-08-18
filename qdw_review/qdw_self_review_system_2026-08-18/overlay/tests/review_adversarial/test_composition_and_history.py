from qdw.system import QDWSystem
from qdw.ideas.service import IdeaService

def test_qdw_system_composes_global_canonical_services(tmp_path):
    q=QDWSystem(tmp_path/"qdw.db")
    for attr in ("world","pain","stack","opportunities","ideas","human","contractors","products","watch","catalog"):
        assert hasattr(q,attr), f"QDWSystem missing canonical service: {attr}"

def test_cemetery_retains_multiple_historical_burials(tmp_path):
    q=QDWSystem(tmp_path/"qdw.db")
    ideas=IdeaService(q.db,q.ledger)
    iid,_=ideas.propose(problem_key="p",solution_key="s",title="x",summary="x",customer="c",product_form="api")
    ideas.bury(iid,"TOO_EXPENSIVE",assumptions={"cost":10},revisit_triggers=[{"cost_below":1}])
    ideas.revive(iid,{"cost_below":1})
    ideas.bury(iid,"NO_DISTRIBUTION",assumptions={"channels":0},revisit_triggers=[{"channels_above":0}])
    with q.db.connect() as con:
        n=con.execute("SELECT COUNT(*) FROM cemetery_entries WHERE idea_id=?",(iid,)).fetchone()[0]
    assert n == 2
