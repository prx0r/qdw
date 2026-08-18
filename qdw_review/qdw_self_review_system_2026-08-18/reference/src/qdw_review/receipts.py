from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
import json, os, subprocess, time, uuid
from typing import Sequence

def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00","Z")

@dataclass(frozen=True)
class Receipt:
    receipt_id:str
    module_id:str
    argv:tuple[str,...]
    cwd:str
    started_at:str
    finished_at:str
    duration_ms:int
    exit_code:int
    status:str
    stdout_path:str
    stderr_path:str
    stdout_sha256:str
    stderr_sha256:str

    def to_dict(self):return asdict(self)

class ReceiptRunner:
    def __init__(self,out_dir:str|Path):
        self.out=Path(out_dir);self.out.mkdir(parents=True,exist_ok=True)

    def run(self,module_id:str,argv:Sequence[str],cwd:str|Path,timeout:int=600)->Receipt:
        rid="review_receipt_"+uuid.uuid4().hex
        d=self.out/rid;d.mkdir()
        start=now();t0=time.monotonic()
        try:
            p=subprocess.run(list(argv),cwd=Path(cwd),capture_output=True,timeout=timeout)
            code=p.returncode;stdout=p.stdout;stderr=p.stderr
        except subprocess.TimeoutExpired as e:
            code=124;stdout=e.stdout or b"";stderr=e.stderr or b""
            if isinstance(stdout,str):stdout=stdout.encode()
            if isinstance(stderr,str):stderr=stderr.encode()
        finish=now()
        op=d/"stdout.log";ep=d/"stderr.log"
        op.write_bytes(stdout);ep.write_bytes(stderr)
        r=Receipt(
            rid,module_id,tuple(argv),str(Path(cwd).resolve()),start,finish,
            int((time.monotonic()-t0)*1000),code,"PASS" if code==0 else "FAIL",
            str(op),str(ep),sha256(stdout).hexdigest(),sha256(stderr).hexdigest()
        )
        (d/"receipt.json").write_text(json.dumps(r.to_dict(),indent=2),encoding="utf-8")
        return r
