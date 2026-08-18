"""Strict numbered migrations with immutable digests and explicit legacy baseline adoption."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json,re

from qdw.core.db import Database

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "migrations"

class MigrationError(RuntimeError): pass
class MigrationDrift(MigrationError): pass
class MigrationBaselineRequired(MigrationError): pass

def _hash_file(path:Path)->str:
    return sha256(path.read_bytes()).hexdigest()

def _sql_quote(value:str)->str:
    return "'" + value.replace("'","''") + "'"

def _migration_files(mdir:Path)->list[tuple[int,Path]]:
    out=[]
    seen=set()
    for p in sorted(mdir.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        version=int(p.name.split("_",1)[0])
        if version in seen:raise MigrationError(f"duplicate migration version {version}")
        seen.add(version);out.append((version,p))
    return out

def _ensure_table(db:Database)->None:
    with db.connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS schema_versions (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL,
            content_hash TEXT,
            filename TEXT,
            baseline_note TEXT
        );
        """)
        cols={r["name"] for r in con.execute("PRAGMA table_info(schema_versions)").fetchall()}
        for name,decl in (
            ("content_hash","TEXT"),
            ("filename","TEXT"),
            ("baseline_note","TEXT"),
        ):
            if name not in cols:
                con.execute(f"ALTER TABLE schema_versions ADD COLUMN {name} {decl}")

def applied_versions(db:Database)->set[int]:
    _ensure_table(db)
    with db.connect() as con:
        return {r["version"] for r in con.execute("SELECT version FROM schema_versions").fetchall()}

def schema_fingerprint(db:Database)->str:
    with db.connect() as con:
        rows=con.execute("""
            SELECT type,name,tbl_name,sql FROM sqlite_master
            WHERE name NOT LIKE 'sqlite_%' AND name!='schema_versions'
            ORDER BY type,name
        """).fetchall()
    normalized=[
        {
            "type":r["type"],
            "name":r["name"],
            "table":r["tbl_name"],
            "sql":" ".join((r["sql"] or "").split()),
        }
        for r in rows
    ]
    return sha256(json.dumps(normalized,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def verify_applied_migrations(db:Database,migrations_dir:str|Path|None=None)->None:
    _ensure_table(db)
    mdir=Path(migrations_dir) if migrations_dir else _MIGRATIONS_DIR
    files=dict(_migration_files(mdir))
    with db.connect() as con:
        rows=con.execute(
            "SELECT version,content_hash,filename FROM schema_versions ORDER BY version"
        ).fetchall()
    for row in rows:
        version=row["version"]
        if version not in files:
            raise MigrationDrift(f"applied migration {version} file is missing")
        if not row["content_hash"]:
            raise MigrationBaselineRequired(
                f"MIGRATION_BASELINE_REQUIRED: version {version} has no trusted digest"
            )
        actual=_hash_file(files[version])
        if actual!=row["content_hash"]:
            raise MigrationDrift(
                f"MIGRATION_DRIFT: version {version}: expected {row['content_hash']}, got {actual}"
            )
        if row["filename"] and row["filename"]!=files[version].name:
            raise MigrationDrift(
                f"MIGRATION_FILENAME_DRIFT: version {version}: {row['filename']} != {files[version].name}"
            )

def _apply_one(db:Database,version:int,path:Path)->None:
    digest=_hash_file(path)
    filename=path.name
    sql=path.read_text(encoding="utf-8")
    # Include the version record in the same explicit SQLite transaction as the migration body.
    script=(
        "BEGIN IMMEDIATE;\n"
        + sql
        + "\nINSERT INTO schema_versions(version,applied_at,content_hash,filename,baseline_note) VALUES("
        + str(version)
        + ",strftime('%Y-%m-%dT%H:%M:%fZ','now'),"
        + _sql_quote(digest)+","+_sql_quote(filename)+",NULL);\nCOMMIT;\n"
    )
    con=db.connect()
    try:
        con.executescript(script)
    except Exception:
        try:con.execute("ROLLBACK")
        except Exception:pass
        raise
    finally:
        con.close()

def migrate(db:Database,migrations_dir:str|Path|None=None)->list[int]:
    _ensure_table(db)
    mdir=Path(migrations_dir) if migrations_dir else _MIGRATIONS_DIR
    if not mdir.exists():return []
    files=_migration_files(mdir)
    # Existing applied rows must be trustworthy before applying anything new.
    if applied_versions(db):
        verify_applied_migrations(db,mdir)
    applied=applied_versions(db)
    newly=[]
    for version,path in files:
        if version in applied:continue
        _apply_one(db,version,path)
        newly.append(version)
    verify_applied_migrations(db,mdir)
    return newly

def migrate_all(db:Database,migrations_dir:str|Path|None=None)->None:
    migrate(db,migrations_dir)

def adopt_legacy_baseline(db:Database,*,migrations_dir:str|Path|None=None,
                          trusted_schema_fingerprint:str,actor:str,note:str)->dict:
    """One-time explicit adoption for old rows created before migration hashes existed.

    The caller must supply a trusted schema fingerprint obtained from a known-good historical build.
    We never silently trust current migration bytes.
    """
    _ensure_table(db)
    current=schema_fingerprint(db)
    if current!=trusted_schema_fingerprint:
        raise MigrationBaselineRequired(
            f"schema fingerprint mismatch: trusted={trusted_schema_fingerprint}, current={current}"
        )
    mdir=Path(migrations_dir) if migrations_dir else _MIGRATIONS_DIR
    files=dict(_migration_files(mdir))
    adopted=[]
    with db.tx(immediate=True) as con:
        rows=con.execute(
            "SELECT version,content_hash FROM schema_versions ORDER BY version"
        ).fetchall()
        for row in rows:
            if row["content_hash"]:continue
            version=row["version"]
            if version not in files:
                raise MigrationBaselineRequired(f"migration file missing for legacy version {version}")
            digest=_hash_file(files[version])
            baseline=f"{actor}: {note}; schema={trusted_schema_fingerprint}"
            con.execute("""UPDATE schema_versions
                SET content_hash=?,filename=?,baseline_note=? WHERE version=?""",
                (digest,files[version].name,baseline,version))
            adopted.append(version)
    verify_applied_migrations(db,mdir)
    return {"schema_fingerprint":current,"adopted_versions":adopted}
