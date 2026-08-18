from datetime import datetime,timezone,timedelta
import pytest
from qdw.core.scheduling.service import due,next_after
def test_interval():
    now=datetime(2026,1,1,tzinfo=timezone.utc)
    assert due(None,60,now)
    assert not due(now,60,now)
    assert due(now,60,now+timedelta(seconds=60))
def test_minimum():
    with pytest.raises(ValueError):next_after(None,10)
