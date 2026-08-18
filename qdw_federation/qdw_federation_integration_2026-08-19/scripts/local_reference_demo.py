from qdw_federation import *
from qdw_federation.adapters.gitgoblin import GitGoblinAdapter
from qdw_federation.adapters.dell import DellAdapter
from qdw_federation.adapters.forge import ForgeAdapter
from qdw_federation.fakes import FakeForgeTransport,forge_asset
from qdw_federation.store import FederationStore
from qdw_federation.router import QDWReferenceRouter
from qdw_federation.verifier import ReferenceQDWVerifier

store=FederationStore();kernel=FederationKernel(store,QDWReferenceRouter())

gg=GitGoblinAdapter().market_records_to_batch([{
 "observation_id":"o","oracle_id":"gg","entity_id":"repo:x","observed_at":"now",
 "source_family":"frontier_attention","sector":"ai","metric":"momentum","value":.9,"unit":"score",
 "evidence":{"artifact_sha256":"a"*64},"quality":{"confidence":.9}
}],cursor="demo")
print("GitGoblin ingest:",kernel.ingest_frontier(gg))

snap,adv=DellAdapter().resolve_to_snapshot({"capability":"api.build"},{
 "recommended":{"offer_id":"o","model_id":"m","provider_id":"p","score":80,"estimated_cost":.05},
 "alternatives":[],"excluded":[],"decision":{"status":"RESOLVED","method":"demo","as_of":"now"}
})
kernel.register_resource_snapshot(snap,adv)

transport=FakeForgeTransport([forge_asset(cost=.005,quality=.95)])
forge=ForgeAdapter(transport)
choice=kernel.choose(capability="api.build",snapshot=snap,forge_assets=forge.assets("api.build"),
                     quality_floor=.7,max_cost_usd=.1)
print("QDW final choice:",choice)

out,cert=kernel.execute_forge(
 forge=forge,choice=choice,capability="api.build",arguments={"task":"demo"},request_id="demo",
 work_ref=FederatedRef("qdw","work_node","node-demo",digest="sha256:node"),
 verifier=ReferenceQDWVerifier(),max_spend_usd=.1)
print("Forge result:",out.status,out.invocation_ref.object_id)
print("QDW certificate:",cert.status,cert.certificate_id)
