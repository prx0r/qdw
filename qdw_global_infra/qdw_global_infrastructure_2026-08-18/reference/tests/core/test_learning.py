from qdw.core.db import Database
from qdw.core.portfolio.learning import FactoryLearning
def test_posterior(tmp_path):
    db=Database(tmp_path/"x.db");db.migrate();l=FactoryLearning(db)
    l.update("api","1",certified=True,outcome_success=True,utility=.8,cost_usd=.1)
    p=l.posterior("api","1")
    assert p.runs==1 and p.mean_success>.5 and abs(p.mean_cost-.1)<1e-9
