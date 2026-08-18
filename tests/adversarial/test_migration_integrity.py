"""Applied migration bytes are immutable."""

import pytest

from qdw.core.db import Database
from qdw.core.migrations import migrate, migrate_all


def test_applied_migration_drift_is_rejected(tmp_path):
    d = Database(tmp_path / "db.sqlite")
    migrate_all(d)
    m = tmp_path / "migrations"
    m.mkdir()
    # Use version 9999 to avoid collision with real migrations
    p = m / "9999_test.sql"
    p.write_text("CREATE TABLE drift_test(id INTEGER);")
    migrate(d, m)
    # Now change the file — drift must be rejected
    p.write_text("CREATE TABLE drift_test(id INTEGER); CREATE TABLE drift_extra(id INTEGER);")
    with pytest.raises(ValueError, match="(?i)drift|checksum|immutable"):
        migrate(d, m)
