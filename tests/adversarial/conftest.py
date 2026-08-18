from pathlib import Path
import pytest
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger

@pytest.fixture
def db(tmp_path:Path):
    d=Database(tmp_path/"qdw.db")
    d.migrate()
    return d

@pytest.fixture
def ledger(db):
    return Ledger(db)
