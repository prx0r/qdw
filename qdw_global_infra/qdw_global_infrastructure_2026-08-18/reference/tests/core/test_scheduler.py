from qdw.core.graph.scheduler import Candidate,choose,opportunity_cost,allocation_index
def test_negative_work_withheld():
    assert choose([Candidate("a",1,2)]) is None
def test_best_positive():
    a=Candidate("a",3,1);b=Candidate("b",2,.5)
    assert choose([a,b]).node_id=="a"
    assert opportunity_cost(a,[a,b])<0
def test_exploration_shrinks():
    assert allocation_index(.5,1,100)>allocation_index(.5,50,100)
