import os,uuid,httpx
from qdw_lab.httpcheck import get_json,post_json,forge_headers
def ensure_fixture(urls):
    return post_json(urls["forge"],"/v1/lab/ensure-fixture",
                     {"capability":"fixture.echo"},headers=forge_headers())


def test_gitgoblin_to_qdw_world(urls):
    export=get_json(urls["gitgoblin"],"/v1/export/qdw")
    result=post_json(urls["qdw"],"/v1/federation/sync/gitgoblin",{})
    assert result["status"] in {"OK","OK_EMPTY"}
    assert result["snapshot_id"]
    assert result.get("batch_digest")==export.get("batch_digest")

def test_forgejo_to_forge_asset_provenance(urls):
    token=os.environ.get("FORGE_ADMIN_TOKEN","lab-admin-token")
    r=httpx.post(urls["forge"]+"/v1/admin/forgejo/sync",
                 headers={"X-QDW-Admin-Token":token},
                 json={"base_url":urls["forgejo"],"org":"qdw","token":"fixture-token","page_size":25},
                 timeout=30)
    r.raise_for_status();x=r.json()
    assert x["repos_seen"]>50
    assert x["assets_registered"]>0
    assert x["errors"]==[]
    assets=get_json(urls["forge"],"/v1/assets",params={"capability":"fixture.echo"})
    assert assets
    for a in assets[:3]:
        prov=a["provenance"]
        assert prov["source_commit"]
        assert prov["source_manifest_digest"].startswith("sha256:")

def test_dell_snapshot_reaches_qdw_but_remains_advisory(urls):
    ensure_fixture(urls)
    x=post_json(urls["qdw"],"/v1/federation/refresh",{
       "capability":"fixture.echo","workload":{"task":"fixture.echo","input_tokens_per_request":100,
       "output_tokens_per_request":10,"requests":1},"max_cost_usd":1})
    assert x["dell"]["authority"]=="ADVISORY"
    assert x["route_count"]>=1

def test_full_qdw_forge_execution_and_certificate(urls):
    ensure_fixture(urls)
    aid="v11-"+uuid.uuid4().hex
    x=post_json(urls["qdw"],"/v1/federation/execute",{
      "attempt_id":aid,"capability":"fixture.echo",
      "arguments":{"message":"finish-line"},"max_spend_usd":1})
    assert x["state"]=="COMMITTED"
    assert x["route"]["provider_id"]=="forge"
    assert x["external_invocation_id"]
    assert x["certificate_id"]
    assert x["cost_usd"]>=0

    inv=get_json(urls["forge"],f"/v1/invocations/{x['external_invocation_id']}")
    assert inv["status"]=="VERIFIED"
    assert inv["verification_certificate_id"]==x["certificate_id"]

    q=get_json(urls["qdw"],f"/v1/federation/attempts/{aid}")
    assert q["state"]=="COMMITTED"
    assert q["cost_event_id"]

def test_exact_attempt_replay_does_not_double_charge_or_learn(urls):
    ensure_fixture(urls)
    aid="v11-replay-"+uuid.uuid4().hex
    body={"attempt_id":aid,"capability":"fixture.echo","arguments":{"x":1},"max_spend_usd":1}
    a=post_json(urls["qdw"],"/v1/federation/execute",body)
    b=post_json(urls["qdw"],"/v1/federation/execute",body)
    assert a["external_invocation_id"]==b["external_invocation_id"]
    assert a["cost_event_id"]==b["cost_event_id"]
    assert a["learning_event_id"]==b["learning_event_id"]

def test_changed_attempt_payload_is_conflict(urls):
    ensure_fixture(urls)
    aid="v11-conflict-"+uuid.uuid4().hex
    post_json(urls["qdw"],"/v1/federation/execute",{
      "attempt_id":aid,"capability":"fixture.echo","arguments":{"x":1},"max_spend_usd":1})
    r=httpx.post(urls["qdw"]+"/v1/federation/execute",json={
      "attempt_id":aid,"capability":"fixture.echo","arguments":{"x":2},"max_spend_usd":1},timeout=20)
    assert r.status_code==409

def test_qdw_never_returns_external_unverified_result_as_success(urls):
    # Contract surface explicitly exposes verifier state.
    schema=get_json(urls["qdw"],"/v1/federation/protocol")
    assert "SUCCEEDED_UNVERIFIED" not in schema["terminal_success_states"]
    assert schema["terminal_success_states"]==["COMMITTED"]
