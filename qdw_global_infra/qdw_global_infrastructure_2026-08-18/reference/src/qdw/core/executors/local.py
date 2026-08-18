from __future__ import annotations
from typing import Callable
from .protocol import ExecutionRequest,ExecutionResult

class LocalExecutor:
    executor_id="local"
    def __init__(self,handlers:dict[str,Callable[[ExecutionRequest],dict]]):
        self.handlers=handlers
    def execute(self,request:ExecutionRequest)->ExecutionResult:
        fn=self.handlers.get(request.task_kind)
        if not fn:return ExecutionResult(False,"unsupported")
        try:return ExecutionResult(True,"ok",final=fn(request))
        except Exception as e:return ExecutionResult(False,"failed",stderr=repr(e))
