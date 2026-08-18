from __future__ import annotations
from dataclasses import asdict,is_dataclass
from enum import Enum
import hashlib,json
from typing import Any

def norm(x:Any)->Any:
    if is_dataclass(x): return norm(asdict(x))
    if isinstance(x,Enum): return x.value
    if isinstance(x,dict): return {str(k):norm(v) for k,v in sorted(x.items(),key=lambda kv:str(kv[0]))}
    if isinstance(x,(list,tuple)): return [norm(v) for v in x]
    return x

def canonical(x:Any)->str:
    return json.dumps(norm(x),sort_keys=True,separators=(",",":"),ensure_ascii=False)

def digest(x:Any)->str:
    return "sha256:"+hashlib.sha256(canonical(x).encode()).hexdigest()
