"""Applied migration bytes are immutable."""

from pathlib import Path
import pytest
from qdw.core.db import Database
from qdw.core.migrations import migrate

def test_applied_migration_drift_is_rejected(tmp_path):
    d=Database(tmp_path/"db.sqlite")
    with d.connect() as con:
        con.execute("CREATE TABLE schema_versions(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    m=tmp_path/"migrations";m.mkdir()
    p=m/"0001_x.sql";p.write_text("CREATE TABLE x(id INTEGER);")
    migrate(d,m)
    p.write_text("CREATE TABLE x(id INTEGER); CREATE TABLE y(id INTEGER);")
    with pytest.raises(Exception,match="(?i)drift|checksum|immutable"):
        migrate(d,m)
