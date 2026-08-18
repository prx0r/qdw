from qdw_lab.repo import text,repo

def test_qdw_export_module_exists():
    assert (repo("gitgoblin")/"gitgoblin/integrations/qdw.py").exists()

def test_qdw_export_endpoint_exists():
    s=text("gitgoblin","gitgoblin/api.py")
    assert "/v1/export/qdw" in s

def test_legacy_export_is_not_qdw_runtime_dependency():
    s=text("gitgoblin","gitgoblin/api.py")
    assert "integrations.qdw" in s
