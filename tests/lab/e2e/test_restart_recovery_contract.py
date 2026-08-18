import uuid
from qdw_lab.httpcheck import post_json,get_json

def test_resume_endpoint_is_idempotent_without_restart(urls):
    aid="resume-"+uuid.uuid4().hex
    first=post_json(urls["qdw"],"/v1/federation/execute",{
       "attempt_id":aid,"capability":"fixture.echo","arguments":{"x":"resume"},
       "max_spend_usd":1,"debug_stop_after":"SUCCEEDED_UNVERIFIED"})
    assert first["state"]=="SUCCEEDED_UNVERIFIED"
    second=post_json(urls["qdw"],"/v1/federation/resume",{"attempt_id":aid})
    assert second["state"]=="COMMITTED"
    third=post_json(urls["qdw"],"/v1/federation/resume",{"attempt_id":aid})
    assert third["state"]=="COMMITTED"
    assert third["external_invocation_id"]==second["external_invocation_id"]
