import json
from qdw.core.db import Database
from qdw.core.factories.registry import FactoryRegistry
def test_version_immutable(tmp_path):
    db=Database(tmp_path/"x.db");db.migrate();r=FactoryRegistry(db)
    m={"factory_id":"x","version":"1","kind":"api","name":"X","phases":["build"],
       "mandatory_teams":[],"conditional_teams":{},"default_budget_usd":0,
       "fixture":{"fixture_id":"x","max_cost_usd":0}}
    p=tmp_path/"m.json";p.write_text(json.dumps(m));r.register_manifest(p)
    m["name"]="changed";p.write_text(json.dumps(m))
    try:
        r.register_manifest(p);assert False
    except ValueError:
        pass
