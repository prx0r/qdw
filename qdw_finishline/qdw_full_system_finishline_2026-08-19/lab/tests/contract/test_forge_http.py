import uuid
import httpx
from qdw_lab.httpcheck import get_json,post_json,forge_headers

def fixture(urls):
    return post_json(urls["forge"],"/v1/lab/ensure-fixture",
                     {"capability":"fixture.echo"},headers=forge_headers())

def lease(urls,asset,operations):
    return post_json(urls["forge"],"/v1/leases",{
       "capability":"fixture.echo","asset_id":asset["asset_id"],"version":asset["version"],
       "calls":1,"max_spend_usd":1,"allowed_operations":operations},headers=forge_headers())

def test_assets_endpoint_returns_versions_and_manifest_hash(urls):
    xs=get_json(urls["forge"],"/v1/assets")
    for a in xs:
        assert a.get("asset_id") and a.get("version")
        assert a.get("manifest_hash")
        if a.get("status")=="ACTIVE":assert a.get("certificate_id")

def test_verification_contract_has_no_legacy_boolean(urls):
    x=get_json(urls["forge"],"/v1/protocol")
    fields=set(x["schemas"]["invocation_verification"].get("fields",[]))
    assert "certificate" in fields
    assert "pass"+"ed" not in fields

def test_bad_lease_token_cannot_use_idempotency_result(urls):
    a=fixture(urls);l=lease(urls,a,["invoke"]);rid="lab-"+uuid.uuid4().hex
    first=post_json(urls["forge"],"/v1/invoke",{
       "lease_token":l["token"],"capability":"fixture.echo",
       "arguments":{"x":1},"client_request_id":rid},headers=forge_headers())
    r=httpx.post(urls["forge"]+"/v1/invoke",json={
       "lease_token":"definitely-wrong","capability":"fixture.echo",
       "arguments":{"x":1},"client_request_id":rid},headers=forge_headers(),timeout=10)
    assert r.status_code in {400,401,403}
    assert first["invocation_id"]

def test_disallowed_invoke_operation_is_rejected(urls):
    a=fixture(urls);l=lease(urls,a,["inspect"])
    r=httpx.post(urls["forge"]+"/v1/invoke",json={
       "lease_token":l["token"],"capability":"fixture.echo","arguments":{},
       "client_request_id":"bad-op-"+uuid.uuid4().hex},headers=forge_headers(),timeout=10)
    assert r.status_code in {400,401,403}
