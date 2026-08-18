from __future__ import annotations
import os

PRODUCTION_AUTHORITIES={
  "EstateRouter","EstateVerificationService","EstateScheduler","EstateWorkGraphAuthority"
}

def assert_incubator_only(component:str):
    if component in PRODUCTION_AUTHORITIES:
        raise PermissionError(
          f"{component} is incubator-only; QDW owns production WorkGraph/routing/verification authority")
    return True

def production_enabled()->bool:
    # This environment variable intentionally does not unlock authority. It only documents intent.
    return False
