"""HotSwap failure classification — error types, circuit breaker."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ErrorClass(StrEnum):
    AUTH = "AUTH"
    TRANSIENT_RATE_LIMIT = "TRANSIENT_RATE_LIMIT"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    SERVER = "SERVER"
    CONTEXT = "CONTEXT"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    TASK_FAILURE = "TASK_FAILURE"
    SAFETY_POLICY = "SAFETY_POLICY"
    UNKNOWN = "UNKNOWN"


QUOTA_PHRASES = (
    "daily limit", "weekly limit", "quota exceeded", "quota_exceeded",
    "resource exhausted", "resource_exhausted", "tokens per day",
    "session usage limit", "upgrade for higher limits",
)


def classify_error(status: int | None, message: str = "", retry_after: float | None = None) -> ErrorClass:
    m = (message or "").lower()
    if status in (401, 403):
        return ErrorClass.AUTH
    if "context length" in m or "maximum context" in m:
        return ErrorClass.CONTEXT
    if any(p in m for p in QUOTA_PHRASES):
        return ErrorClass.QUOTA_EXHAUSTED
    if status == 429:
        return ErrorClass.TRANSIENT_RATE_LIMIT
    if status is not None and status >= 500:
        return ErrorClass.SERVER
    if "malformed" in m or "empty response" in m:
        return ErrorClass.INVALID_RESPONSE
    if "safety" in m or "policy refusal" in m:
        return ErrorClass.SAFETY_POLICY
    return ErrorClass.UNKNOWN


@dataclass
class CircuitBreaker:
    threshold: int = 3
    failures: int = 0
    state: str = "CLOSED"

    def record_failure(self, error: ErrorClass):
        if error in {ErrorClass.SERVER, ErrorClass.TRANSIENT_RATE_LIMIT, ErrorClass.INVALID_RESPONSE}:
            self.failures += 1
            if self.failures >= self.threshold:
                self.state = "OPEN"

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"
