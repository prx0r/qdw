from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator

class Database:
    def __init__(self,path:str|Path):
        self.path=str(path)

    def connect(self)->sqlite3.Connection:
        con=sqlite3.connect(self.path,timeout=30,isolation_level=None)
        con.row_factory=sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=5000")
        return con

    def migrate(self,schema_path:str|Path|None=None)->None:
        schema_path=schema_path or Path(__file__).with_name("schema.sql")
        sql=Path(schema_path).read_text(encoding="utf-8")
        with self.connect() as con:
            con.executescript(sql)

    @contextmanager
    def tx(self,immediate:bool=False)->Iterator[sqlite3.Connection]:
        con=self.connect()
        try:
            con.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
