from qdw_lab.repo import text
def test_finishline_federation_api_exists():
    s=text("qdw","src/qdw/interfaces/api.py")
    for route in (
      "/v1/federation/sync/gitgoblin","/v1/federation/refresh",
      "/v1/federation/execute","/v1/federation/resume",
      "/v1/federation/attempts/{attempt_id}","/v1/federation/protocol"):
        assert route in s
