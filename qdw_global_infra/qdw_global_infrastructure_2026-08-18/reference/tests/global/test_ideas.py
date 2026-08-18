import pytest
from qdw.ideas.dossier import build_dossier

def test_idea_dedupe_transfer_cemetery_revival(system):
    a,created=system.ideas.propose(problem_key="invoice sync",solution_key="normalized api",title="Invoice API",
        summary="Normalize invoice sync",customer="developers",product_form="api")
    b,created2=system.ideas.propose(problem_key="invoice sync",solution_key="normalized api",title="Different title",
        summary="same",customer="developers",product_form="api")
    assert created and not created2 and a==b
    app=system.ideas.transfer(a,"app")
    assert app!=a
    system.ideas.bury(a,"TOO_EXPENSIVE",assumptions={"cost":10},
                      revisit_triggers=[{"cost_below":1}])
    assert system.ideas.cemetery()[0]["status"]=="DORMANT"
    system.ideas.revive(a,{"cost_below":1})
    assert system.ideas.cemetery()[0]["status"]=="REVIVED"

def test_review_pipeline_cannot_skip_stages(system):
    idea,_=system.ideas.propose(problem_key="p",solution_key="s",title="X",summary="x",customer="c",product_form="api")
    with pytest.raises(ValueError):
        system.idea_reviews.review(idea,"ARCHITECTURE_REVIEW",passed=True,score={},reason_codes=[],snapshot={})
    for stage in ("DISCOVERY","EVIDENCE_REVIEW","ADVERSARIAL_REVIEW","PORTFOLIO_REVIEW","ARCHITECTURE_REVIEW","BUILD_READY"):
        system.idea_reviews.review(idea,stage,passed=True,score={"x":1},reason_codes=[],snapshot={"stage":stage})
    assert system.idea_reviews.next_stage(idea) is None

def test_dossier_has_example_domains_and_hash(system):
    idea_id,_=system.ideas.propose(problem_key="api replacement",solution_key="matcher",title="Alternative API",
        summary="Find substitutes",customer="agents",product_form="api")
    with system.db.connect() as con:
        idea=dict(con.execute("SELECT * FROM ideas WHERE idea_id=?",(idea_id,)).fetchone())
    d=build_dossier(idea,{"sources":3},{"score":.8},["competition"])
    assert d.example_domains and d.report_hash
