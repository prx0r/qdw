import pytest
from qdw.ideas.service import IdeaService
from qdw.ideas.pipeline import IdeaReviewPipeline
from qdw.ideas.review_evidence import IdeaReviewEvidenceService

def test_cemetery_history_append_only(db,ledger):
    ideas=IdeaService(db,ledger)
    iid,_=ideas.propose(
        problem_key="p",solution_key="s",title="x",summary="x",
        customer="c",product_form="api"
    )
    first=ideas.bury(iid,"TOO_EXPENSIVE",assumptions={"cost":10},revisit_triggers=[{"cost_below":1}])
    ideas.revive(iid,{"cost_below":1})
    second=ideas.bury(iid,"NO_DISTRIBUTION",assumptions={"channels":0},revisit_triggers=[{"channels_above":0}])
    assert first!=second
    with db.connect() as con:
        rows=con.execute("""SELECT episode_no,reason_code,status FROM cemetery_entries
            WHERE idea_id=? ORDER BY episode_no""",(iid,)).fetchall()
    assert [(r["episode_no"],r["reason_code"]) for r in rows]==[
        (1,"TOO_EXPENSIVE"),(2,"NO_DISTRIBUTION")
    ]
    assert rows[0]["status"]=="REVIVED"
    assert rows[1]["status"]=="DORMANT"

def test_pipeline_requires_bound_evidence(db,ledger):
    ideas=IdeaService(db,ledger)
    iid,_=ideas.propose(
        problem_key="p",solution_key="s",title="x",summary="x",
        customer="c",product_form="api"
    )
    evidence=IdeaReviewEvidenceService(db,ledger)
    pipeline=IdeaReviewPipeline(db,ideas,evidence)
    with pytest.raises(TypeError):
        pipeline.review(iid,"DISCOVERY",passed=True,score={},reason_codes=[],snapshot={})
