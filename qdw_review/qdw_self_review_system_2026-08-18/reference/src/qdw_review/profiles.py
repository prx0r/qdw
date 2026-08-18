from __future__ import annotations
import sys

PROFILES = {
    "quick": [],
    "full": [
        [sys.executable,"-m","compileall","-q","src/qdw","tests"],
        ["ruff","check","src/qdw","tests"],
        ["pyright","src/qdw"],
        [sys.executable,"-m","pytest","tests/unit","tests/contract","tests/adversarial","tests/integration","-q"],
    ],
    "release": [
        [sys.executable,"-m","compileall","-q","src/qdw","tests"],
        ["ruff","check","src/qdw","tests"],
        ["pyright","src/qdw"],
        [sys.executable,"-m","pytest","-q"],
        [sys.executable,"-m","build","--wheel"],
        ["docker","build","--no-cache","-t","qdw:review","."],
    ],
}
