from gitgoblin.integrations.qdw import SCHEMA

def test_schema_name_is_versioned():
    assert SCHEMA.endswith("/1")
