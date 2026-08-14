"""Integration test for Phase 38 graph observation checkpoints."""

from pathlib import Path

from aeroragx.agent.checkpointing import JsonCheckpointStore
from aeroragx.agent.persistence import CheckpointObserver
from aeroragx.agent.state import AgentState


def test_observer_writes_monotonic_checkpoints(tmp_path: Path) -> None:
    observer = CheckpointObserver(JsonCheckpointStore(tmp_path))
    state = AgentState(
        request_id="r1",
        thread_id="t1",
        original_query="q",
        current_query="q",
    )
    observer(state)
    observer(state.advance_step())

    latest = observer.store.latest("t1")
    assert latest is not None
    assert latest.sequence == 2
    assert latest.state.step_number == 1
