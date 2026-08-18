from __future__ import annotations
from dataclasses import asdict,is_dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any

def normalize(obj:Any)->Any:
    if is_dataclass(obj): return normalize(asdict(obj))
    if isinstance(obj,Enum): return obj.value
    if isinstance(obj,dict): return {str(k):normalize(v) for k,v in sorted(obj.items(),key=lambda x:str(x[0]))}
    if isinstance(obj,(list,tuple)): return [normalize(x) for x in obj]
    return obj

def canonical_json(obj:Any)->str:
    return json.dumps(normalize(obj),sort_keys=True,separators=(",",":"),ensure_ascii=False)

def digest(obj:Any)->str:
    return "sha256:"+sha256(canonical_json(obj).encode()).hexdigest()
