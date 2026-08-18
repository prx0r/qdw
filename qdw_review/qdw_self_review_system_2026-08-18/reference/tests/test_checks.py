from qdw_review.repo import Repo
from qdw_review.checks.proof import ProofCheck
from qdw_review.checks.trust import TrustBoundaryCheck
from qdw_review.checks.provenance import ProvenanceCheck
from qdw_review.checks.workgraph import WorkGraphCheck
from qdw_review.checks.hotswap import HotSwapCheck
from qdw_review.checks.migrations import MigrationCheck
from qdw_review.checks.schema import SchemaCheck
from qdw_review.checks.contractors import ContractorCheck
from qdw_review.checks.products import ProductCheck
from qdw_review.checks.ideas import IdeaCheck
from qdw_review.checks.composition import CompositionCheck
from qdw_review.checks.docker_ci import DockerCICheck
from qdw_review.checks.e2e import E2ECheck
from qdw_review.checks.interfaces import InterfaceCheck
from qdw_review.checks.human import HumanQueueCheck
from qdw_review.checks.claims import ClaimConsistencyCheck

def ids(result): return {x.rule_id for x in result.findings}

def test_proof_detects_vacuity(broken_repo):
    x=ids(ProofCheck().run(Repo(broken_repo)))
    assert {"QDW-PROOF-001","QDW-PROOF-002","QDW-PROOF-003"} <= x

def test_trust_detects_substitution(broken_repo):
    x=ids(TrustBoundaryCheck().run(Repo(broken_repo)))
    assert {"QDW-TRUST-001","QDW-TRUST-002","QDW-TRUST-003","QDW-TRUST-004"} <= x

def test_provenance_detects_split_transaction(broken_repo):
    assert "QDW-PROV-001" in ids(ProvenanceCheck().run(Repo(broken_repo)))

def test_workgraph_detects_unknown_and_retry(broken_repo):
    x=ids(WorkGraphCheck().run(Repo(broken_repo)))
    assert {"QDW-GRAPH-001","QDW-GRAPH-002","QDW-GRAPH-003"} <= x

def test_hotswap_detects_race_and_routes(broken_repo):
    x=ids(HotSwapCheck().run(Repo(broken_repo)))
    assert {"QDW-HOTSWAP-001","QDW-HOTSWAP-002","QDW-HOTSWAP-003"} <= x

def test_migration_contract_findings(broken_repo):
    x=ids(MigrationCheck().run(Repo(broken_repo)))
    assert {"QDW-MIG-001","QDW-MIG-002","QDW-MIG-003"} <= x

def test_schema_runs(broken_repo):
    SchemaCheck().run(Repo(broken_repo))

def test_contractor_detects_mutability(broken_repo):
    x=ids(ContractorCheck().run(Repo(broken_repo)))
    assert {"QDW-CONTRACTOR-001","QDW-CONTRACTOR-002"} <= x

def test_product_detects_lineage_outcome(broken_repo):
    x=ids(ProductCheck().run(Repo(broken_repo)))
    assert {"QDW-PRODUCT-001","QDW-PRODUCT-002"} <= x

def test_idea_detects_history_overwrite(broken_repo):
    assert "QDW-IDEA-001" in ids(IdeaCheck().run(Repo(broken_repo)))

def test_composition_detects_missing_services(broken_repo):
    assert "QDW-ARCH-001" in ids(CompositionCheck().run(Repo(broken_repo)))

def test_docker_ci_detects_install_order(broken_repo):
    x=ids(DockerCICheck().run(Repo(broken_repo)))
    assert {"QDW-CI-001","QDW-CI-002","QDW-CI-003"} <= x

def test_e2e_detects_missing_spine(broken_repo):
    assert "QDW-E2E-001" in ids(E2ECheck().run(Repo(broken_repo)))

def test_interface_detects_direct_mcp_test(broken_repo):
    assert "QDW-IFACE-001" in ids(InterfaceCheck().run(Repo(broken_repo)))

def test_human_detects_actor_gap(broken_repo):
    assert "QDW-HUMAN-001" in ids(HumanQueueCheck().run(Repo(broken_repo)))

def test_claim_consistency(broken_repo):
    x=ids(ClaimConsistencyCheck().run(Repo(broken_repo)))
    assert "QDW-CLAIM-002" in x
