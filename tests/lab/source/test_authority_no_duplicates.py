from qdw_lab.repo import text

def test_qdw_system_does_not_construct_sandbox_estate_authority():
    s=text("qdw","src/qdw/system.py")
    assert "EstateRouter(" not in s
    assert "EstateVerificationService(" not in s

def test_qdw_federation_does_not_write_external_sqlite():
    s=text("qdw","src/qdw/federation/service.py")
    assert "qdw_forge.db" not in s
    assert "gitgoblin.db" not in s
    assert "canonical_db" not in s
