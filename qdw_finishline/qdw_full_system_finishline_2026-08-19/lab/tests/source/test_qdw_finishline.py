from pathlib import Path
from qdw_lab.repo import text,repo

def test_fake_forge_client_removed_from_production():
    p=repo("qdw")/"src/qdw/federation/forge_client.py"
    assert not p.exists(), "production simulated Forge client still exists; move test double under tests only"

def test_qdw_system_composes_real_federation_runtime():
    s=text("qdw","src/qdw/system.py")
    assert "compose_federation" in s
    assert "federation_runtime" in s

def test_qdw_retires_local_forge_lease_secret_state_in_new_migration():
    s=text("qdw","migrations/0011_federation_finishline.sql")
    assert "DROP TABLE forge_leases" in s
    assert "DROP TABLE forge_invocation_certs" in s
    assert "token TEXT" not in s
    from qdw_lab.repo import repo
    for py in (repo("qdw")/"src/qdw").rglob("*.py"):
        text_py=py.read_text(errors="replace")
        assert "forge_leases" not in text_py, f"production code still depends on retired local Forge lease table: {py}"

def test_route_persistence_handles_fixed_request_cost():
    s=text("qdw","src/qdw/hotswap/persistent.py")
    assert s.count("fixed_request_cost_usd")>=3, "field must appear in INSERT/update/load paths"

def test_real_e2e_tests_exist():
    d=repo("qdw")/"tests/e2e"
    xs=[p for p in d.glob("test_*.py")]
    assert xs, "tests/e2e has no real test modules"

def test_qdw_forge_integration_does_not_import_local_simulator():
    s=text("qdw","tests/integration/test_estate_forge_integration.py")
    assert "qdw.federation.forge_client" not in s
    assert "passed\": True" not in s and "'passed': True" not in s

def test_qdw_known_dell_cost_loss_not_accepted():
    s=text("qdw","tests/integration/test_dell_integration.py")
    assert "known issue" not in s.lower()
    assert "loses cost" not in s.lower()
