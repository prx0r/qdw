from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from qdw.core import canonical_json,hash_object,new_id,utc_now
from qdw.hotswap.types import TaskSpec
from .contracts import CapabilityExecutionRequest,FederatedRef
from .candidates import FederatedCandidateCollector
from .route_bindings import FederatedRouteRegistry

_STATES={
 "DISCOVERING","CANDIDATES_READY","ROUTED","RUNNING","SUCCEEDED_UNVERIFIED",
 "VERIFYING","VERIFIED","COMMITTED","FAILED"
}

class FederationAttemptConflict(RuntimeError):pass

class FederationRuntime:
    """Canonical cross-service execution state machine.

    QDW owns this state. External services never mutate QDW lifecycle rows.
    """

    def __init__(self,system,*,federation,certificates,verification_policies,artifacts_dir=".qdw/federation"):
        self.system=system;self.federation=federation;self.certificates=certificates
        self.policies=verification_policies
        self.artifacts_dir=Path(artifacts_dir);self.artifacts_dir.mkdir(parents=True,exist_ok=True)
        self.collector=FederatedCandidateCollector()
        self.bindings=FederatedRouteRegistry(system,federation.store)

    def _attempt(self,attempt_id):
        with self.system.db.connect() as con:
            r=con.execute("SELECT * FROM federation_attempts_v2 WHERE attempt_id=?",(attempt_id,)).fetchone()
        return dict(r) if r else None

    def _create_or_validate(self,*,attempt_id,capability,arguments,task,work_node_id=None,factory_run_id=None):
        request={"capability":capability,"arguments":arguments,"task":asdict(task),
                 "work_node_id":work_node_id,"factory_run_id":factory_run_id}
        rd=hash_object(request);old=self._attempt(attempt_id)
        if old:
            if old["request_digest"]!=rd:raise FederationAttemptConflict("ATTEMPT_REQUEST_MISMATCH")
            return old
        now=utc_now()
        with self.system.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO federation_attempts_v2(
              attempt_id,work_node_id,factory_run_id,task_cell_id,capability,request_digest,request_json,
              state,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,'DISCOVERING',?,?)""",
            (attempt_id,work_node_id,factory_run_id,task.cell_id,capability,rd,
             canonical_json(request).decode(),now,now))
            self.system.ledger.append_in_tx(con,"federation.attempt_created","federation_attempt",attempt_id,{
              "capability":capability,"request_digest":rd,"work_node_id":work_node_id,
            })
        return self._attempt(attempt_id)

    def _set(self,attempt_id,state,**fields):
        if state not in _STATES:raise ValueError(state)
        allowed={
          "route_id","route_binding_digest","external_lease_id","external_invocation_id",
          "external_output_digest","quoted_cost_usd","actual_cost_usd","certificate_id","failure_json"
        }
        if set(fields)-allowed:raise KeyError(set(fields)-allowed)
        cols=["state=?","updated_at=?"];vals=[state,utc_now()]
        for k,v in fields.items():cols.append(f"{k}=?");vals.append(v)
        vals.append(attempt_id)
        with self.system.db.tx(immediate=True) as con:
            con.execute(f"UPDATE federation_attempts_v2 SET {','.join(cols)} WHERE attempt_id=?",vals)
            self.system.ledger.append_in_tx(con,"federation.attempt_state","federation_attempt",attempt_id,{
              "state":state,**{k:v for k,v in fields.items() if k!="failure_json"}})
        return self._attempt(attempt_id)

    def refresh_candidates(self,*,capability,task:TaskSpec):
        request={
          "workload":{"task":task.task_kind,"input_tokens_per_request":task.estimated_input_tokens,
                      "output_tokens_per_request":task.estimated_output_tokens,"requests":1},
          "constraints":{"max_total_cost_usd":task.task_budget_usd,
                         "context_tokens_min":task.context_tokens_min,
                         "tools":"required" if task.tools_required else "any",
                         "json_schema":"required" if task.json_required else "any"},
        }
        snap,adv,snapshot_id,advisory_id=self.federation.dell_candidates(request)
        dell=self.collector.dell(snap)
        forge_raw=self.federation.forge_assets(capability)
        forge=self.collector.forge(forge_raw,source_snapshot_digest=None)
        for binding in dell:
            self.bindings.register(binding,snapshot_id=snapshot_id,advisory_id=advisory_id)
        for binding in forge:
            self.bindings.register(binding)
        dell_ids={x.route.route_id for x in dell}
        forge_ids={x.route.route_id for x in forge}
        retired={
          "dell":self.bindings.reconcile_source("dell",dell_ids),
          "forge":self.bindings.reconcile_source("forge",forge_ids)}
        return {"dell_snapshot":snap,"dell_advisory":adv,
                "route_ids":[x.route.route_id for x in [*dell,*forge]],"retired":retired}

    def _selected_binding(self,route_id):
        row=self.bindings.binding(route_id)
        return row,FederatedRef(
          row["system_id"],row["object_type"],row["object_id"],
          version=row["object_version"],revision=row["object_revision"],digest=row["object_digest"])

    def execute(self,*,attempt_id,capability,arguments,task:TaskSpec,
                work_node_id=None,factory_run_id=None,verification_cwd=".",stop_after=None):
        row=self._create_or_validate(
          attempt_id=attempt_id,capability=capability,arguments=arguments,task=task,
          work_node_id=work_node_id,factory_run_id=factory_run_id)
        if row["state"]=="COMMITTED":return self.result(attempt_id)
        if row["state"]=="FAILED":return self.result(attempt_id)

        if row["state"]=="DISCOVERING":
            self.refresh_candidates(capability=capability,task=task)
            row=self._set(attempt_id,"CANDIDATES_READY")
            if stop_after=="CANDIDATES_READY":return self.result(attempt_id)

        if row["state"]=="CANDIDATES_READY":
            plan=self.system.router.plan(task,self.system.route_registry.active())
            if not plan.primary:
                return self._set(attempt_id,"FAILED",failure_json=canonical_json({"reason":"NO_ROUTE"}).decode())
            chosen=plan.primary.route
            binding,external_ref=self._selected_binding(chosen.route_id)
            row=self._set(
              attempt_id,"ROUTED",route_id=chosen.route_id,
              route_binding_digest=binding["binding_digest"],
              quoted_cost_usd=chosen.request_cost(task))
            if stop_after=="ROUTED":return self.result(attempt_id)

        if row["state"] in {"ROUTED","RUNNING"}:
            binding,external_ref=self._selected_binding(row["route_id"])
            if binding["route_kind"]!="FORGE_CAPABILITY":
                return self._set(attempt_id,"FAILED",failure_json=canonical_json({
                  "reason":"NON_FORGE_ROUTE_EXECUTOR_NOT_IMPLEMENTED_BY_FEDERATION_RUNTIME",
                  "route_kind":binding["route_kind"]}).decode())
            self._set(attempt_id,"RUNNING")
            req=CapabilityExecutionRequest(
              request_id=attempt_id,capability=capability,selected_asset=external_ref,
              arguments=arguments,max_spend_usd=task.task_budget_usd,
              qdw_work_node_id=work_node_id or "",qdw_route_digest=row["route_binding_digest"])
            outcome=self.federation.forge.execute(req)
            if outcome.status!="SUCCEEDED_UNVERIFIED":
                self._commit_effects(attempt_id,task,success=False,cost=float(outcome.cost_usd or 0),
                                     evidence_ref=f"forge:{outcome.invocation.object_id}")
                return self._set(attempt_id,"FAILED",
                  external_invocation_id=outcome.invocation.object_id,
                  actual_cost_usd=outcome.cost_usd,
                  failure_json=canonical_json({"reason":outcome.failure or outcome.status}).decode())
            row=self._set(
              attempt_id,"SUCCEEDED_UNVERIFIED",
              external_invocation_id=outcome.invocation.object_id,
              external_output_digest=outcome.output_digest,
              actual_cost_usd=outcome.cost_usd)
            artifact_dir=self.artifacts_dir/attempt_id;artifact_dir.mkdir(parents=True,exist_ok=True)
            output_path=artifact_dir/"output.json";output_path.write_text(
              canonical_json(outcome.output).decode(),encoding="utf-8")
            if stop_after=="SUCCEEDED_UNVERIFIED":return self.result(attempt_id)

        if row["state"]=="SUCCEEDED_UNVERIFIED":
            self._set(attempt_id,"VERIFYING")
            output_path=self.artifacts_dir/attempt_id/"output.json"
            plan=self.policies.plan(capability,output_path)
            run_id=self.system.verification.execute(
              plan,task_id=f"federation:{attempt_id}",cwd=verification_cwd,require_clean=False)
            inv_ref=FederatedRef("forge","invocation",row["external_invocation_id"],
                                 digest=row["external_output_digest"])
            cert=self.certificates.issue(
              verification_run_id=run_id,subject=inv_ref,output_digest=row["external_output_digest"])
            # Forge resolves the certificate reference through QDW or a configured signature policy.
            self.federation.forge.bind_certificate_reference(
              row["external_invocation_id"],cert)
            if cert.status!="VERIFIED":
                row=self._set(attempt_id,"FAILED",certificate_id=cert.certificate_id,
                              failure_json=canonical_json({
                                "reason":"VERIFICATION_REJECTED",
                                "certificate_id":cert.certificate_id}).decode())
                self._commit_effects(attempt_id,task,success=False,cost=float(row["actual_cost_usd"] or 0),
                                     evidence_ref=f"forge:{row['external_invocation_id']}")
                return self.result(attempt_id)
            row=self._set(attempt_id,"VERIFIED",certificate_id=cert.certificate_id)
            if stop_after=="VERIFIED":return self.result(attempt_id)

        if row["state"]=="VERIFIED":
            if work_node_id:
                # WorkGraph acceptance remains independently explicit.
                with self.system.db.connect() as con:
                    node=con.execute("SELECT state FROM work_nodes WHERE node_id=?",(work_node_id,)).fetchone()
                if node and node["state"]=="RUNNING":self.system.graphs.verifying(work_node_id)
                if node and node["state"] in {"RUNNING","VERIFYING"}:
                    self.system.graphs.complete(work_node_id,{
                      "federation_attempt_id":attempt_id,"certificate_id":row["certificate_id"],
                      "external_invocation_id":row["external_invocation_id"]})
            self._commit_effects(
              attempt_id,task,success=True,cost=float(row["actual_cost_usd"] or 0),
              evidence_ref=f"forge:{row['external_invocation_id']}")
            row=self._set(attempt_id,"COMMITTED")

        return self.result(attempt_id)

    def _commit_effects(self,attempt_id,task,*,success,cost,evidence_ref):
        row=self._attempt(attempt_id);route_id=row["route_id"]
        # Initialize route posterior under canonical HotSwap logic before the atomic once-only effect.
        route=self.system.route_registry.get(route_id)
        self.system.bandits.get(task.cell_id,route)
        cost_id="cost_fed_"+attempt_id
        learn_id="learn_fed_"+attempt_id
        with self.system.db.tx(immediate=True) as con:
            old=con.execute("SELECT learning_event_id FROM federation_learning_effects WHERE attempt_id=?",
                            (attempt_id,)).fetchone()
            if old:return
            con.execute("""INSERT OR IGNORE INTO cost_events(
              cost_event_id,factory_run_id,node_id,category,provider,amount_usd,quantity,unit,occurred_at,evidence_ref
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (cost_id,row["factory_run_id"],row["work_node_id"],"federation_execution",
             route.provider_id,cost,1,"invocation",utc_now(),evidence_ref))
            con.execute("""UPDATE route_posteriors SET
              alpha=alpha+?,beta=beta+?,updated_at=? WHERE cell_id=? AND route_id=?""",
              (1.0 if success else 0.0,0.0 if success else 1.0,utc_now(),task.cell_id,route_id))
            con.execute("""INSERT INTO federation_learning_effects(
              learning_event_id,attempt_id,cell_id,route_id,success,weight,applied_at
            ) VALUES(?,?,?,?,?,1.0,?)""",
              (learn_id,attempt_id,task.cell_id,route_id,1 if success else 0,utc_now()))
            con.execute("""UPDATE federation_attempts_v2 SET cost_event_id=?,learning_event_id=?,updated_at=?
                           WHERE attempt_id=?""",(cost_id,learn_id,utc_now(),attempt_id))
            self.system.ledger.append_in_tx(con,"federation.effects_committed","federation_attempt",attempt_id,{
              "cost_event_id":cost_id,"learning_event_id":learn_id,"success":success,"amount_usd":cost})
        return {"cost_event_id":cost_id,"learning_event_id":learn_id}

    def result(self,attempt_id):
        r=self._attempt(attempt_id)
        if not r:raise KeyError(attempt_id)
        out={k:r[k] for k in (
          "attempt_id","work_node_id","factory_run_id","capability","state","route_id",
          "external_invocation_id","external_output_digest","quoted_cost_usd","actual_cost_usd",
          "certificate_id","cost_event_id","learning_event_id","failure_json")}
        out["cost_usd"]=r["actual_cost_usd"]
        if r["route_id"]:
            route=self.system.route_registry.get(r["route_id"])
            out["route"]={"route_id":route.route_id,"provider_id":route.provider_id,"model_id":route.model_id}
        return out
