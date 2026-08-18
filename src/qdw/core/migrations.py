"""Migration runner — numbered, idempotent, content-hashed.

Each migration records its content SHA-256. If a migration file changes
after being applied, the runner detects the drift and refuses to proceed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from qdw.core.db import Database

_MIGRATIONS_DIR = Path(__file__).parent.parent.parent.parent / "migrations"


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def applied_versions(db: Database) -> set[int]:
    with db.connect() as con:
        try:
            rows = con.execute("SELECT version FROM schema_versions ORDER BY version").fetchall()
            return {r["version"] for r in rows}
        except Exception:
            return set()


def _check_drift(db: Database, version: int, content_hash: str) -> None:
    """Check if a migration file changed after being applied."""
    with db.connect() as con:
        row = con.execute(
            "SELECT content_hash FROM schema_versions WHERE version=?", (version,)
        ).fetchone()
        if row and row["content_hash"] and row["content_hash"] != content_hash:
            raise ValueError(
                f"MIGRATION_DRIFT: migration {version} changed after being applied. "
                f"Expected {row['content_hash']}, got {content_hash}. "
                f"Create a new migration instead of modifying applied ones."
            )


def migrate(db: Database, migrations_dir: str | Path | None = None) -> list[int]:
    """Apply all unapplied migrations in order. Returns newly applied versions."""
    mdir = Path(migrations_dir) if migrations_dir else _MIGRATIONS_DIR
    if not mdir.exists():
        return []

    applied = applied_versions(db)
    files = sorted(mdir.glob("*.sql"))
    newly_applied = []

    for f in files:
        stem = f.stem
        try:
            version = int(stem.split("_")[0])
        except (ValueError, IndexError):
            continue

        content_hash = _hash_file(f)

        # Check for drift on already-applied migrations
        if version in applied:
            _check_drift(db, version, content_hash)
            continue

        sql = f.read_text(encoding="utf-8")
        with db.connect() as con:
            con.executescript(sql)
            con.execute(
                """INSERT INTO schema_versions(version, applied_at, content_hash)
                VALUES(?, datetime('now'), ?)""",
                (version, content_hash),
            )

        newly_applied.append(version)

    return newly_applied


def migrate_all(db: Database) -> None:
    """Ensure schema_versions exists with content_hash column, then apply pending."""
    with db.connect() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS schema_versions (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL,
                content_hash TEXT
            );
        """)
    migrate(db)
