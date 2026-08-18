"""Persistent bandit observations must not be lost under synchronized concurrency."""

import threading

from qdw.core.db import Database
from qdw.hotswap.persistent import PersistentBanditStore


def test_two_concurrent_successes_are_both_counted(tmp_path,monkeypatch):
    d=Database(tmp_path/"qdw.db");d.migrate()
    store=PersistentBanditStore(d)
    barrier=threading.Barrier(2)
    original=store._upsert

    def synchronized_upsert(cell_id,route_id,posterior):
        barrier.wait(timeout=5)
        return original(cell_id,route_id,posterior)

    monkeypatch.setattr(store,"_upsert",synchronized_upsert)
    errors=[]
    def work():
        try: store.update("coding","route-x",True)
        except Exception as e: errors.append(e)

    a=threading.Thread(target=work);b=threading.Thread(target=work)
    a.start();b.start();a.join();b.join()
    assert not errors
    with d.connect() as con:
        row=con.execute("SELECT alpha,beta FROM route_posteriors WHERE cell_id='coding' AND route_id='route-x'").fetchone()
    # prior for update-without-row is alpha=1; two successes => 3.
    assert row["alpha"] == 3.0
