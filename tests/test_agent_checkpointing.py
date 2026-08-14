"""Tests for Phase 38 checkpoint persistence."""

from pathlib import Path

from aeroragx.agent.checkpointing import AgentCheckpoint, JsonCheckpointStore
from aeroragx.agent.state import AgentState


def test_checkpoint_roundtrip(tmp_path: Path) -> None:
    state = AgentState(
        request_id="r1",
        thread_id="t1",
        original_query="q",
        current_query="q",
    )
    checkpoint = AgentCheckpoint(
        checkpoint_id="cp1",
        thread_id="t1",
        sequence=1,
        state=state,
    )
    store = JsonCheckpointStore(tmp_path)
    path = store.save(checkpoint)

    assert store.load(path) == checkpoint
    assert store.latest("t1") == checkpoint
