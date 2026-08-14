"""Node-level checkpoint observer for the Phase 37 graph."""

from __future__ import annotations

from dataclasses import dataclass, field

from aeroragx.agent.checkpointing import AgentCheckpoint, JsonCheckpointStore
from aeroragx.agent.state import AgentState


@dataclass(slots=True)
class CheckpointObserver:
    """Persist one immutable checkpoint for every observed graph-state change."""

    store: JsonCheckpointStore
    prefix: str = "agent"
    _sequence: int = field(init=False, default=0)

    def __call__(self, state: AgentState) -> None:
        if self._sequence == 0:
            latest = self.store.latest(state.thread_id)
            if latest is not None:
                self._sequence = latest.sequence
        self._sequence += 1
        self.store.save(
            AgentCheckpoint(
                checkpoint_id=f"{self.prefix}-{self._sequence:06d}",
                thread_id=state.thread_id,
                sequence=self._sequence,
                state=state,
            )
        )
