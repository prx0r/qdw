def test_qdw_system_has_one_canonical_route_authority(tmp_path):
    from qdw.system import QDWSystem
    q=QDWSystem(tmp_path/"q.db",enable_review=False)
    assert q.router is not None
    assert q.graphs is not None
    assert q.verification is not None
    assert q.federation is not None
    # Federation is an adapter/composition layer, not an alternate scheduler/router/verifier.
    assert not hasattr(q.federation,"graphs")
    assert not hasattr(q.federation,"router")
    assert not hasattr(q.federation,"verification")
