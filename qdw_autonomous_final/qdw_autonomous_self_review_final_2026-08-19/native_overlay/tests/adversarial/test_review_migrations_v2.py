from pathlib import Path
import pytest
from qdw.core.db import Database
from qdw.core.migrations import (
    MigrationBaselineRequired,MigrationDrift,migrate,migrate_all,schema_fingerprint
)

def _db(path):
    return Database(path)

def test_migration_drift(tmp_path):
    m=tmp_path/"m";m.mkdir()
    p=m/"0001_x.sql";p.write_text("CREATE TABLE x(id INTEGER PRIMARY KEY);")
    db=_db(tmp_path/"a.db")
    migrate(db,m)
    p.write_text("CREATE TABLE x(id INTEGER PRIMARY KEY, changed TEXT);")
    with pytest.raises(MigrationDrift):
        migrate(db,m)

def test_null_digest_requires_baseline(tmp_path):
    m=tmp_path/"m";m.mkdir()
    (m/"0001_x.sql").write_text("CREATE TABLE x(id INTEGER PRIMARY KEY);")
    db=_db(tmp_path/"a.db");migrate(db,m)
    with db.connect() as con:
        con.execute("UPDATE schema_versions SET content_hash=NULL WHERE version=1")
    with pytest.raises(MigrationBaselineRequired):
        migrate(db,m)

def test_migration_failure_atomic(tmp_path):
    m=tmp_path/"m";m.mkdir()
    (m/"0001_bad.sql").write_text("""
        CREATE TABLE first_table(id INTEGER);
        THIS IS INVALID SQL;
        CREATE TABLE never_table(id INTEGER);
    """)
    db=_db(tmp_path/"a.db")
    with pytest.raises(Exception):
        migrate(db,m)
    with db.connect() as con:
        assert con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='first_table'").fetchone() is None
        assert con.execute("SELECT 1 FROM schema_versions WHERE version=1").fetchone() is None

def test_populated_upgrade_parity(tmp_path):
    old=tmp_path/"old";old.mkdir()
    (old/"0001_x.sql").write_text("CREATE TABLE x(id INTEGER PRIMARY KEY, value TEXT);")
    db_upgrade=_db(tmp_path/"upgrade.db")
    migrate(db_upgrade,old)
    with db_upgrade.connect() as con:
        con.execute("INSERT INTO x(id,value) VALUES(1,'preserve-me')")
    (old/"0002_y.sql").write_text("CREATE TABLE y(id INTEGER PRIMARY KEY, x_id INTEGER REFERENCES x(id));")
    migrate(db_upgrade,old)

    fresh=tmp_path/"fresh";fresh.mkdir()
    for p in old.iterdir():
        (fresh/p.name).write_bytes(p.read_bytes())
    db_fresh=_db(tmp_path/"fresh.db")
    migrate(db_fresh,fresh)

    assert schema_fingerprint(db_upgrade)==schema_fingerprint(db_fresh)
    with db_upgrade.connect() as con:
        assert con.execute("SELECT value FROM x WHERE id=1").fetchone()["value"]=="preserve-me"
        assert con.execute("PRAGMA foreign_key_check").fetchall()==[]
