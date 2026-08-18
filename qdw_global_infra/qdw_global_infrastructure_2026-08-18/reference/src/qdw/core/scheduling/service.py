from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone

@dataclass(frozen=True)
class IntervalSchedule:
    schedule_id:str
    target_type:str
    target_id:str
    every_seconds:int
    budget_usd:float|None=None

def next_after(last:datetime|None,every_seconds:int,now:datetime|None=None)->datetime:
    if every_seconds<60:raise ValueError("minimum interval 60 seconds")
    now=now or datetime.now(timezone.utc)
    return now if last is None else last+timedelta(seconds=every_seconds)

def due(last:datetime|None,every_seconds:int,now:datetime|None=None)->bool:
    now=now or datetime.now(timezone.utc)
    return next_after(last,every_seconds,now)<=now
