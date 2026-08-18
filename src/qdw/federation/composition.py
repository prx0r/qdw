from __future__ import annotations
from .config import FederationConfig
from .http_clients import GitGoblinHTTPClient,DellHTTPClient,ForgeHTTPClient
from .store import FederationStore
from .service import FederationService
from .gitgoblin_adapter import GitGoblinFederationAdapter
from .dell_adapter import DellFederationAdapter
from .forge_adapter import ForgeExecutionAdapter
from .external_certificates import ExternalCertificateService
from .verification_policies import VerificationPolicyRegistry
from .runtime import FederationRuntime

def compose_federation(system,*,repo_root="."):
    cfg=FederationConfig.from_env()
    store=FederationStore(system.db,system.ledger,getattr(system,"artifacts",None))
    gg_client=GitGoblinHTTPClient(cfg.gitgoblin_url,timeout=cfg.request_timeout_seconds) if cfg.gitgoblin_url else None
    dell_client=DellHTTPClient(cfg.dell_url,timeout=cfg.request_timeout_seconds) if cfg.dell_url else None
    forge_client=ForgeHTTPClient(
      cfg.forge_url,client_key=cfg.forge_client_key,timeout=cfg.request_timeout_seconds
    ) if cfg.forge_url else None

    if gg_client:store.register_system("gitgoblin","ORACLE","qdw-federation-observation/1",cfg.gitgoblin_url)
    if dell_client:store.register_system("dell","ORACLE","qdw-federation-resource/1",cfg.dell_url)
    if forge_client:store.register_system("forge","CAPABILITY_EXCHANGE","qdw-forge/2",cfg.forge_url)

    forge_adapter=ForgeExecutionAdapter(forge_client) if forge_client else None
    service=FederationService(
      system,store=store,
      gitgoblin_client=gg_client,gitgoblin_adapter=GitGoblinFederationAdapter() if gg_client else None,
      dell_client=dell_client,dell_adapter=DellFederationAdapter() if dell_client else None,
      forge_adapter=forge_adapter)
    certs=ExternalCertificateService(system.db,system.ledger,system.verification)
    policies=VerificationPolicyRegistry()
    runtime=FederationRuntime(
      system,federation=service,certificates=certs,verification_policies=policies,
      artifacts_dir=system.repo_root/".qdw/federation")
    return {"config":cfg,"store":store,"service":service,"certificates":certs,
            "policies":policies,"runtime":runtime}
