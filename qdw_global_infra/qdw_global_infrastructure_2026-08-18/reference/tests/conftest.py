from pathlib import Path
import sys, pytest

SRC=Path(__file__).resolve().parents[1]/"src"
if str(SRC) not in sys.path:
    sys.path.insert(0,str(SRC))

from qdw.system import QDWSystem

@pytest.fixture
def system(tmp_path):
    return QDWSystem(tmp_path/"qdw.db")
