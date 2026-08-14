"""Versioned JSON checkpoint persistence for bounded agent state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aeroragx.agent.state import AgentState

CheckpointVersion = Literal["v0_1"]


class AgentCheckpoint(BaseModel):
    """One immutable snapshot of validated agent state."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    checkpoint_version: CheckpointVersion = "v0_1"
    checkpoint_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    state: AgentState


class JsonCheckpointStore:
    """Simple deterministic development checkpoint store."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def save(self, checkpoint: AgentCheckpoint) -> Path:
        thread_dir = self._root / checkpoint.thread_id
        thread_dir.mkdir(parents=True, exist_ok=True)
        path = thread_dir / f"{checkpoint.sequence:06d}-{checkpoint.checkpoint_id}.json"
        if path.exists():
            raise FileExistsError(f"Checkpoint already exists: {path}")
        path.write_text(
            json.dumps(
                checkpoint.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def load(self, path: Path) -> AgentCheckpoint:
        return AgentCheckpoint.model_validate_json(path.read_text(encoding="utf-8"))

    def latest(self, thread_id: str) -> AgentCheckpoint | None:
        thread_dir = self._root / thread_id
        if not thread_dir.exists():
            return None
        candidates = sorted(thread_dir.glob("*.json"))
        if not candidates:
            return None
        return self.load(candidates[-1])
