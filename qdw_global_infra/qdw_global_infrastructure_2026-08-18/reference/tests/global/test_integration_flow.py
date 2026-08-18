from qdw.sources.protocol import SourceResult

def test_world_to_pain_to_opportunity_to_idea_to_product(system):
    obs=system.world.record_source_result(SourceResult.success(
        "forum","forum",[{"id":"1","text":"Exporting usage invoices into accounting is tedious and expensive"}]
    ))[0]
    _,cluster=system.pain.ingest(obs,"Exporting usage invoices into accounting is tedious and expensive",
        intensity=.9,recurrence_hint=.9,machine_solvable=.9,verifiable=.9)
    opp=system.synthesize.from_pain_cluster(cluster,factory_hint="api")
    o=system.opportunities.get(opp)
    idea,_=system.ideas.propose(problem_key=o["problem_key"],solution_key="normalized invoice api",
        title="Invoice Bridge",summary=o["thesis"],customer="developers",product_form="api",opportunity_id=opp)
    prod=system.products.create("Invoice Bridge","invoice-bridge","api",idea_id=idea,factory_id="api",factory_version="1")
    passport=system.products.passport(prod)
    assert passport["idea"]["opportunity_id"]==opp
    assert passport["product"]["factory_id"]=="api"
    assert system.doctor()["ok"]
