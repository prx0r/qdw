"""Offline reference flow proving the global IDs align end-to-end."""
from pathlib import Path
from qdw.system import QDWSystem
from qdw.sources.protocol import SourceResult

db=Path(".qdw/example.db")
db.parent.mkdir(exist_ok=True)
if db.exists():db.unlink()
q=QDWSystem(db)

obs=q.world.record_source_result(SourceResult.success(
    "example-forum","forum",
    [{"id":"p1","text":"Reconciling API usage invoices manually every month is tedious and expensive"}]
))[0]

_,cluster=q.pain.ingest(
    obs,
    "Reconciling API usage invoices manually every month is tedious and expensive",
    intensity=.9,recurrence_hint=.9,machine_solvable=.9,verifiable=.9
)

opp=q.synthesize.from_pain_cluster(cluster,factory_hint="api")
o=q.opportunities.get(opp)
idea,_=q.ideas.propose(
    problem_key=o["problem_key"],
    solution_key="normalized invoice reconciliation api",
    title="Invoice Bridge",
    summary=o["thesis"],
    customer="developers",
    product_form="api",
    opportunity_id=opp,
)

product=q.products.create(
    "Invoice Bridge","invoice-bridge","api",
    idea_id=idea,factory_id="api",factory_version="1.0.0"
)

print(q.products.passport(product))
print(q.doctor())
