from qdw_lab.httpcheck import get_json

def test_qdw_export_exists(urls):
    x=get_json(urls["gitgoblin"],"/v1/export/qdw")
    assert x["schema_version"]=="qdw-federation-observation/1"
    assert x["source_system"]=="gitgoblin"
    assert "cursor" in x and "batch_digest" in x and "observations" in x

def test_opportunity_proposals_are_advisory(urls):
    x=get_json(urls["gitgoblin"],"/v1/export/qdw")
    for p in x.get("opportunity_proposals",[]):
        assert p.get("authority")=="ADVISORY"

def test_export_repeat_has_stable_digest_without_new_scan(urls):
    a=get_json(urls["gitgoblin"],"/v1/export/qdw")
    b=get_json(urls["gitgoblin"],"/v1/export/qdw")
    assert a["batch_digest"]==b["batch_digest"]
