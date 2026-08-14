"""Deterministic fault injection used only by reliability tests and benchmarks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

FaultKind = Literal[
    "timeout",
    "service_error",
    "malformed_response",
    "dependency_unavailable",
]


class InjectedAgentFault(RuntimeError):
    """Base class for deterministic test-only faults."""


class InjectedTimeout(InjectedAgentFault):
    pass


class InjectedServiceError(InjectedAgentFault):
    pass


class InjectedMalformedResponse(InjectedAgentFault):
    pass


class InjectedDependencyUnavailable(InjectedAgentFault):
    pass


@dataclass(slots=True)
class FaultInjector:
    """Raise one selected fault on configured call numbers."""

    fault: FaultKind
    call_numbers: set[int]
    _calls: int = field(init=False, default=0)

    def check(self) -> None:
        self._calls += 1
        if self._calls not in self.call_numbers:
            return
        mapping = {
            "timeout": InjectedTimeout,
            "service_error": InjectedServiceError,
            "malformed_response": InjectedMalformedResponse,
            "dependency_unavailable": InjectedDependencyUnavailable,
        }
        raise mapping[self.fault](f"Injected {self.fault} on call {self._calls}.")
