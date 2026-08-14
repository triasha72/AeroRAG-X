"""Tests for deterministic fault injection."""

import pytest

from aeroragx.agent.faults import FaultInjector, InjectedTimeout


def test_fault_is_injected_on_selected_call_only() -> None:
    injector = FaultInjector(fault="timeout", call_numbers={2})
    injector.check()
    with pytest.raises(InjectedTimeout):
        injector.check()
