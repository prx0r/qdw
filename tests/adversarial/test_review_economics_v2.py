from qdw.core.graph.scheduler import Candidate,choose

def test_unknown_cost_not_zero():
    known=Candidate("known",expected_value=1.0,expected_cost=.2,confidence=1,urgency=0,risk=0)
    unknown=Candidate("unknown",expected_value=1.0,expected_cost=None,confidence=1,urgency=0,risk=0)
    selected=choose([unknown,known])
    assert selected is not None
    assert selected.node_id=="known"

def test_unknown_value_not_default():
    known=Candidate("known",expected_value=.5,expected_cost=.1,confidence=1,urgency=0,risk=0)
    unknown=Candidate("unknown",expected_value=None,expected_cost=0,confidence=1,urgency=0,risk=0)
    selected=choose([unknown,known])
    assert selected is not None
    assert selected.node_id=="known"
