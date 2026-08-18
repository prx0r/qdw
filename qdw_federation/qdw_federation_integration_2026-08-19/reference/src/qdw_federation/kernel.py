from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .models import *
from .store import FederationStore
from .router import QDWReferenceRouter,FinalChoice
from .interfaces import ForgeExchange,QDWVerifier

@dataclass
class FederationKernel:
    """Executable reference proving boundaries across the five repositories."""

    store:FederationStore
    router:QDWReferenceRouter

    def ingest_frontier(self,batch:ObservationBatch)->dict[str,int]:
        return self.store.ingest_batch(batch)

    def register_resource_snapshot(self,snapshot:ResourceCandidateSnapshot,
                                   advisory:DecisionAdvisory|None=None)->None:
        self.store.put_snapshot(snapshot)
        if advisory:self.store.put_advisory(advisory)

    def choose(self,*,capability:str,snapshot:ResourceCandidateSnapshot,
               forge_assets:tuple[CapabilityAssetView,...],quality_floor:float=.7,
               max_cost_usd:float|None=None)->FinalChoice|None:
        # Refuse to misinterpret external outage as empty candidate set.
        if snapshot.status in {ExternalStatus.UNAVAILABLE,ExternalStatus.FAILED,
                               ExternalStatus.INCOMPATIBLE_PROTOCOL,ExternalStatus.UNAUTHORIZED}:
            raise RuntimeError(f"EXTERNAL_RESOURCE_SOURCE_{snapshot.status}")
        return self.router.choose(
            capability=capability,dell_candidates=snapshot.candidates,forge_assets=forge_assets,
            quality_floor=quality_floor,max_cost_usd=max_cost_usd,
        )

    def execute_forge(self,*,forge:ForgeExchange,choice:FinalChoice,capability:str,
                      arguments:dict[str,Any],request_id:str,work_ref:FederatedRef,
                      verifier:QDWVerifier,max_spend_usd:float|None=None)->tuple[InvocationOutcome,VerificationCertificateRef]:
        if choice.route_kind!="forge":raise ValueError("selected route is not Forge")
        req=CapabilityExecutionRequest(
            request_id=request_id,capability=capability,selected_asset_ref=choice.selected_ref,
            arguments=arguments,max_spend_usd=max_spend_usd,qdw_work_ref=work_ref,
            qdw_route_digest=choice.candidate_set_digest,
        )
        outcome=forge.execute(req)
        self.store.put_invocation(outcome)
        # Executor/Forge output cannot self-verify.
        if outcome.status not in {"SUCCEEDED_UNVERIFIED","FAILED"}:
            raise ValueError("unexpected Forge execution status")
        cert=verifier.verify_invocation(outcome,work_ref)
        forge.bind_certificate(outcome,cert)
        self.store.put_certificate(cert)
        return outcome,cert
