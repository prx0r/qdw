from .claims import ClaimConsistencyCheck
from .composition import CompositionCheck
from .contractors import ContractorCheck
from .docker_ci import DockerCICheck
from .e2e import E2ECheck
from .hotswap import HotSwapCheck
from .human import HumanQueueCheck
from .ideas import IdeaCheck
from .interfaces import InterfaceCheck
from .migrations import MigrationCheck
from .products import ProductCheck
from .proof import ProofCheck
from .provenance import ProvenanceCheck
from .release_integrity import ReleaseIntegrityCheck
from .schema import SchemaCheck
from .test_quality import TestQualityCheck
from .trust import TrustBoundaryCheck
from .workgraph import WorkGraphCheck

ALL_CHECKS = [
    ProofCheck,
    TrustBoundaryCheck,
    ProvenanceCheck,
    WorkGraphCheck,
    HotSwapCheck,
    MigrationCheck,
    SchemaCheck,
    ContractorCheck,
    ProductCheck,
    IdeaCheck,
    CompositionCheck,
    DockerCICheck,
    E2ECheck,
    InterfaceCheck,
    TestQualityCheck,
    HumanQueueCheck,
    ClaimConsistencyCheck,
    ReleaseIntegrityCheck,
]
