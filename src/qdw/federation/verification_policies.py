from __future__ import annotations
import sys
from pathlib import Path
from qdw.proof.plan import VerificationPlan,VerificationCommand

class VerificationPolicyRegistry:
    """Data-driven mapping from capability to a concrete QDW VerificationPlan.

    Unknown capabilities fail closed. Product/factory capabilities should register their own acceptance plan.
    """
    def __init__(self):
        self._builders={"fixture.echo":self._fixture_echo}

    def register(self,capability:str,builder):
        if not capability or not callable(builder):raise ValueError("invalid verification policy")
        self._builders[capability]=builder

    def plan(self,capability:str,output_path:str|Path)->VerificationPlan:
        try:builder=self._builders[capability]
        except KeyError as e:raise ValueError(f"NO_VERIFICATION_POLICY:{capability}") from e
        return builder(Path(output_path))

    @staticmethod
    def _fixture_echo(path:Path)->VerificationPlan:
        return VerificationPlan(
          plan_id="federation.fixture.echo",version="1.0.0",
          commands=(VerificationCommand(
             command_id="verify-output",
             argv=(sys.executable,"-m","qdw.federation.verify_output","fixture.echo",str(path)),
             required=True,timeout_seconds=30,expected_exit_code=0),),
          artifacts=(str(path),)
        )
