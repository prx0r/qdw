from __future__ import annotations
import json,subprocess
from dataclasses import dataclass

@dataclass(frozen=True)
class BeadRef:
    issue_id:str

class BeadsMirror:
    """Optional mirror. Factory OS remains canonical."""
    def __init__(self,binary:str="bd"):self.binary=binary

    def _run(self,*args:str):
        p=subprocess.run([self.binary,*args,"--json"],text=True,capture_output=True)
        if p.returncode!=0:raise RuntimeError(p.stderr.strip() or p.stdout.strip())
        return json.loads(p.stdout) if p.stdout.strip() else None

    def create(self,title:str,description:str,priority:int=2)->BeadRef:
        out=self._run("create",title,"--description",description,"-t","task","-p",str(priority))
        return BeadRef(out.get("id") if isinstance(out,dict) else out[0]["id"])

    def block(self,blocked:str,blocker:str)->None:
        self._run("dep","add",blocked,blocker)

    def discovered(self,title:str,parent:str,description:str)->BeadRef:
        out=self._run("create",title,"--description",description,"-t","task","-p","2",
                      "--deps",f"discovered-from:{parent}")
        return BeadRef(out.get("id") if isinstance(out,dict) else out[0]["id"])
