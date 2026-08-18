from qdw.sources.protocol import SourceResult

def test_source_failure_is_not_empty_success(system):
    failed=system.world.record_source_result(SourceResult.failure("x","forum","rate_limited",context={"q":"a"}))
    empty=system.world.record_source_result(SourceResult.success("x","forum",[],context={"q":"b"}))
    with system.db.connect() as con:
        a=con.execute("SELECT status,error_code FROM observations WHERE observation_id=?",(failed[0],)).fetchone()
        b=con.execute("SELECT status,error_code FROM observations WHERE observation_id=?",(empty[0],)).fetchone()
    assert a["status"]=="ERROR" and a["error_code"]=="rate_limited"
    assert b["status"]=="OK_EMPTY" and b["error_code"] is None

def test_entity_claim_relation_graph(system):
    a=system.world.upsert_entity("company","Acme",external_key="acme")
    b=system.world.upsert_entity("api","Acme API",external_key="acme-api")
    obs=system.world.record_source_result(SourceResult.success("src","registry",[{"id":"1","name":"Acme API"}]))[0]
    claim=system.world.add_claim("provides",{"api":"Acme API"},observation_id=obs,subject_entity_id=a,confidence=.9)
    rel=system.world.relate(a,"provides",b,supporting_claim_id=claim,confidence=.9)
    g=system.world.graph(a)
    assert g["entity"]["canonical_name"]=="Acme"
    assert any(x["relation_id"]==rel for x in g["relations"])
