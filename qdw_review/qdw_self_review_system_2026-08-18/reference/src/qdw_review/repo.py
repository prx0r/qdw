from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import subprocess
from typing import Iterable

class Repo:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def path(self, rel: str | Path) -> Path:
        return self.root / rel

    def exists(self, rel: str | Path) -> bool:
        return self.path(rel).exists()

    def read(self, rel: str | Path, default: str = "") -> str:
        p = self.path(rel)
        if not p.exists() or not p.is_file():
            return default
        return p.read_text(encoding="utf-8", errors="replace")

    def glob(self, pattern: str) -> list[Path]:
        return sorted(self.root.glob(pattern))

    def rglob(self, pattern: str) -> list[Path]:
        return sorted(self.root.rglob(pattern))

    def rel(self, p: Path) -> str:
        return str(p.resolve().relative_to(self.root))

    def file_hash(self, rel: str | Path) -> str | None:
        p = self.path(rel)
        if not p.exists() or not p.is_file():
            return None
        return sha256(p.read_bytes()).hexdigest()

    def git_sha(self) -> str | None:
        try:
            p = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=self.root,
                capture_output=True, text=True, timeout=5
            )
            return p.stdout.strip() if p.returncode == 0 else None
        except Exception:
            return None

    def git_dirty(self) -> bool | None:
        try:
            p = subprocess.run(
                ["git", "status", "--porcelain"], cwd=self.root,
                capture_output=True, text=True, timeout=5
            )
            return bool(p.stdout.strip()) if p.returncode == 0 else None
        except Exception:
            return None

    def grep(self, needle: str, patterns: Iterable[str] = ("*.py", "*.sql", "*.yml", "*.yaml", "*.toml")):
        hits = []
        for pattern in patterns:
            for p in self.rglob(pattern):
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                if needle in text:
                    hits.append((self.rel(p), text))
        return hits

    def git_history_count(self, rel: str) -> int | None:
        try:
            p = subprocess.run(
                ["git", "log", "--format=%H", "--", rel],
                cwd=self.root, capture_output=True, text=True, timeout=10
            )
            if p.returncode != 0:
                return None
            return len([x for x in p.stdout.splitlines() if x.strip()])
        except Exception:
            return None
