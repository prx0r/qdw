from __future__ import annotations
import json,subprocess
from .protocol import ExecutionRequest,ExecutionResult

class HermesExecutor:
    executor_id="hermes"
    def __init__(self,profile:str|None=None,binary:str="hermes"):
        self.profile,self.binary=profile,binary

    def execute(self,request:ExecutionRequest)->ExecutionResult:
        contract={"instruction":request.prompt,"payload":request.payload,
          "return_contract":{"status":"ok|blocked|failed","summary":"string",
            "artifacts":"array","evidence":"array","failure_class":"string|null"}}
        prompt=("Execute this bounded Factory OS work node. Return ONE JSON object matching "
                "return_contract and no markdown fences.\n"+json.dumps(contract,sort_keys=True))
        cmd=[self.binary]
        if self.profile:cmd+=["-p",self.profile]
        cmd+=["-z",prompt]
        try:
            p=subprocess.run(cmd,cwd=request.workspace,text=True,capture_output=True,
                             timeout=request.timeout_seconds)
        except subprocess.TimeoutExpired as e:
            return ExecutionResult(False,"timeout",stdout=e.stdout or "",stderr=e.stderr or "")
        if p.returncode!=0:
            return ExecutionResult(False,"executor_error",stdout=p.stdout,stderr=p.stderr,exit_code=p.returncode)
        try: final=json.loads(p.stdout.strip())
        except json.JSONDecodeError:
            return ExecutionResult(False,"invalid_result",stdout=p.stdout,stderr=p.stderr,exit_code=p.returncode)
        status=final.get("status","failed")
        return ExecutionResult(status=="ok",status,final=final,stdout=p.stdout,stderr=p.stderr,exit_code=p.returncode)
