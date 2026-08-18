from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from datetime import UTC,datetime
import sqlite3

def _statements(sql:str):
    """Split SQLite scripts using sqlite3.complete_statement so triggers/quoted semicolons stay intact."""
    buf=""
    for line in sql.splitlines(keepends=True):
        buf+=line
        if sqlite3.complete_statement(buf):
            stmt=buf.strip()
            if stmt:
                yield stmt
            buf=""
    if buf.strip():
        if not sqlite3.complete_statement(buf):
            raise RuntimeError("incomplete migration SQL")
        yield buf.strip()

def apply_finishline_migrations(db,root:Path|None=None):
    root=root or Path(__file__).resolve().parents[2]/"migrations"
    files=sorted(root.glob("[0-9][0-9][0-9][0-9]_*.sql"))
    with db.tx(immediate=True) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS schema_versions(
          version INTEGER PRIMARY KEY,filename TEXT NOT NULL UNIQUE,
          content_hash TEXT NOT NULL,applied_at TEXT NOT NULL)""")
    for path in files:
        version=int(path.name.split("_",1)[0]);raw=path.read_bytes();h=sha256(raw).hexdigest()
        with db.connect() as con:
            r=con.execute("SELECT * FROM schema_versions WHERE version=?",(version,)).fetchone()
        if r:
            if r["filename"]!=path.name or r["content_hash"]!=h:
                raise RuntimeError(f"migration drift at version {version}")
            continue
        with db.tx(immediate=True) as con:
            for stmt in _statements(raw.decode()):
                # schema_versions may already exist from the bootstrapping line above.
                con.execute(stmt)
            con.execute(
              "INSERT INTO schema_versions(version,filename,content_hash,applied_at) VALUES(?,?,?,?)",
              (version,path.name,h,datetime.now(UTC).isoformat()))
