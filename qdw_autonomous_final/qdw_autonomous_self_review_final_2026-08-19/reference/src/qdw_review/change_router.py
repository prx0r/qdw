from __future__ import annotations
from fnmatch import fnmatch

DEFAULT_ROUTES = (
    (("migrations/**","src/qdw/core/db.py","src/qdw/core/migrations.py"),
     ("review.migrations","review.database","review.proof","review.redteam")),
    (("src/qdw/core/graph/**",),
     ("review.workgraph","review.concurrency","review.provenance","review.redteam")),
    (("src/qdw/hotswap/**",),
     ("review.hotswap","review.economics","review.concurrency","review.redteam")),
    (("src/qdw/factories/**","manifests/factories/**","tests/factories/**"),
     ("review.factory","review.trust","review.redteam")),
    (("src/qdw/contractors/**","manifests/contractors/**","manifests/reviewers/**"),
     ("review.contractor","review.trust","review.redteam")),
    (("src/qdw/world/**","src/qdw/sources/**"),
     ("review.world","review.sources","review.proof")),
    (("src/qdw/intelligence/**","src/qdw/ideas/**"),
     ("review.intelligence","review.ideas","review.claim-consistency")),
    (("src/qdw/products/**","src/qdw/publishing/**"),
     ("review.products","review.trust","review.redteam")),
    (("src/qdw/human/**",),
     ("review.human","review.security","review.trust")),
    (("src/qdw/interfaces/**","src/qdw/cli.py"),
     ("review.interfaces","review.security","review.redteam")),
    ((".github/**","Dockerfile","pyproject.toml","uv.lock"),
     ("review.ci","review.dependencies","review.security")),
    (("src/qdw/review/**",),
     ("review.self-review","review.trust","review.proof","review.redteam","review.claim-consistency")),
)

ALWAYS=("review.architecture","review.claim-consistency")

def select_reviewers(changed_paths,full:bool=False,all_reviewers=()):
    if full:
        return tuple(sorted(set(all_reviewers or sum((list(r[1]) for r in DEFAULT_ROUTES),[]))|set(ALWAYS)))
    selected=set(ALWAYS)
    for path in changed_paths:
        for patterns,reviewers in DEFAULT_ROUTES:
            if any(fnmatch(path,p) for p in patterns):
                selected.update(reviewers)
    return tuple(sorted(selected))
