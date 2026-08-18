"""Migration runner — numbered, idempotent, transactional."""

from __future__ import annotations

from pathlib import Path

from qdw.core.db import Database

_MIGRATIONS_DIR = Path(__file__).parent.parent.parent.parent / "migrations"


def _list_migrations() -> list[Path]:
    if not _MIGRATIONS_DIR.exists():
        return []
    return sorted(_MIGRATIONS_DIR.glob("*.sql"))


def applied_versions(db: Database) -> set[int]:
    with db.connect() as con:
        try:
            rows = con.execute("SELECT version FROM schema_versions ORDER BY version").fetchall()
            return {r["version"] for r in rows}
        except Exception:
            return set()


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

        if version in applied:
            continue

        sql = f.read_text(encoding="utf-8")
        with db.connect() as con:
            # executescript runs in its own implicit transaction
            con.executescript(sql)
            con.execute(
                "INSERT OR IGNORE INTO schema_versions(version, applied_at) VALUES(?, datetime('now'))",
                (version,),
            )

        newly_applied.append(version)

    return newly_applied


def migrate_all(db: Database) -> None:
    """Ensure schema_versions exists, then apply all pending migrations."""
    with db.connect() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS schema_versions (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            );
        """)
    migrate(db)
