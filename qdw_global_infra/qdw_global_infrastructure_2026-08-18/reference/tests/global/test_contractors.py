import json, pytest

def test_contractor_version_immutable_and_graph_expansion(system,tmp_path):
    m={"contractor_id":"redteam.api","version":"1","team":"red_team","specialization":"api",
       "inputs":["artifact"],"outputs":["report"],"gates":["negative"],"default_budget_usd":.1}
    p=tmp_path/"c.json";p.write_text(json.dumps(m))
    system.contractors.register_manifest(p)
    m["gates"]=["weakened"];p.write_text(json.dumps(m))
    with pytest.raises(ValueError):
        system.contractors.register_manifest(p)
    p.write_text(json.dumps({**m,"version":"2"}))
    system.contractors.register_manifest(p)
    g=system.graphs.create_graph()
    n=system.contractors.expand_to_graph(system.graphs,g,"redteam.api")
    system.graphs.refresh_ready(g)
    claimed=system.graphs.claim_ready("worker",graph_id=g)
    assert claimed["node_id"]==n
    assert claimed["payload"]["contractor_id"]=="redteam.api"
