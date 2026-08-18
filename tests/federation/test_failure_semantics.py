import pytest
from qdw.federation.contracts import ExternalSnapshot,ExternalStatus
from qdw.federation.gitgoblin_adapter import GitGoblinFederationAdapter

def test_gitgoblin_protocol_mismatch_is_error_result_not_empty():
    a=GitGoblinFederationAdapter()
    s=a.normalize({"schema_version":"wrong","observations":[]},{"sector":"ai"})
    assert s.status is ExternalStatus.INCOMPATIBLE_PROTOCOL
    r=a.to_source_result(s)
    assert not r.ok
    assert r.items==()

def test_ok_empty_is_distinct():
    a=GitGoblinFederationAdapter()
    s=a.normalize({"schema_version":a.protocol_version,"cursor":"x","observations":[],
                   "opportunity_proposals":[]},{"sector":"ai"})
    assert s.status is ExternalStatus.OK_EMPTY
    r=a.to_source_result(s)
    assert r.ok and r.items==()
