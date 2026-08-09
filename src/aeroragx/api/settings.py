"""Environment-driven settings for the AeroRAG-X API."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from aeroragx.runtime import (
    DenseBackendName,
    RuntimeConfig,
)

type RuntimeMode = Literal[
    "local",
    "openai",
    "transformers",
]


@dataclass(frozen=True, slots=True)
class ApiRuntimeSettings:
    """Validated API runtime settings."""

    mode: RuntimeMode = "local"

    dense_backend: DenseBackendName = "numpy"

    candidate_top_k: int = 20
    evidence_top_k: int = 5

    def to_runtime_config(
        self,
    ) -> RuntimeConfig:
        """Translate API settings into core runtime configuration."""

        if self.mode == "local":
            return RuntimeConfig(
                dense_backend=self.dense_backend,
                generation_config=Path("configs/generation_v0_1.yaml"),
                sufficiency_config=Path("configs/sufficiency_v0_2_1.yaml"),
                facet_retrieval_config=Path("configs/facet_retrieval_v0_1.yaml"),
                candidate_top_k=self.candidate_top_k,
                evidence_top_k=self.evidence_top_k,
            )

        if self.mode == "transformers":
            return RuntimeConfig(
                dense_backend=self.dense_backend,
                generation_config=Path("configs/generation_transformers_v0_1.yaml"),
                sufficiency_config=Path("configs/sufficiency_v0_2_1.yaml"),
                facet_retrieval_config=Path("configs/facet_retrieval_v0_1.yaml"),
                provider_config=Path("configs/provider_v0_1.yaml"),
                provider_runtime_config=Path("configs/transformers_runtime_v0_1.yaml"),
                candidate_top_k=self.candidate_top_k,
                evidence_top_k=self.evidence_top_k,
            )

        return RuntimeConfig(
            dense_backend=self.dense_backend,
            generation_config=Path("configs/generation_openai_v0_1.yaml"),
            sufficiency_config=Path("configs/sufficiency_v0_2_1.yaml"),
            facet_retrieval_config=Path("configs/facet_retrieval_v0_1.yaml"),
            provider_config=Path("configs/provider_v0_1.yaml"),
            http_transport_config=Path("configs/http_transport_openai_v0_1.yaml"),
            provider_runtime_config=Path("configs/provider_runtime_openai_v0_1.yaml"),
            candidate_top_k=self.candidate_top_k,
            evidence_top_k=self.evidence_top_k,
        )


def _positive_integer(
    *,
    value: str,
    name: str,
) -> int:
    """Parse one positive integer environment variable."""

    try:
        parsed = int(value)

    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc

    if parsed < 1:
        raise ValueError(f"{name} must be at least 1.")

    return parsed


def load_api_runtime_settings(
    environ: Mapping[str, str] | None = None,
) -> ApiRuntimeSettings:
    """Load API runtime settings from environment variables."""

    env = os.environ if environ is None else environ

    raw_mode = (
        env.get(
            "AERORAGX_RUNTIME_MODE",
            "local",
        )
        .strip()
        .lower()
    )

    mode: RuntimeMode

    if raw_mode == "local":
        mode = "local"

    elif raw_mode == "openai":
        mode = "openai"

    elif raw_mode == "transformers":
        mode = "transformers"

    else:
        raise ValueError("AERORAGX_RUNTIME_MODE must be 'local', 'openai', or 'transformers'.")

    raw_dense_backend = (
        env.get(
            "AERORAGX_DENSE_BACKEND",
            "numpy",
        )
        .strip()
        .lower()
    )

    dense_backend: DenseBackendName

    if raw_dense_backend == "numpy":
        dense_backend = "numpy"

    elif raw_dense_backend == "pgvector":
        dense_backend = "pgvector"

    else:
        raise ValueError("AERORAGX_DENSE_BACKEND must be 'numpy' or 'pgvector'.")

    candidate_top_k = _positive_integer(
        value=env.get(
            "AERORAGX_CANDIDATE_TOP_K",
            "20",
        ),
        name="AERORAGX_CANDIDATE_TOP_K",
    )

    evidence_top_k = _positive_integer(
        value=env.get(
            "AERORAGX_EVIDENCE_TOP_K",
            "5",
        ),
        name="AERORAGX_EVIDENCE_TOP_K",
    )

    if evidence_top_k > candidate_top_k:
        raise ValueError("AERORAGX_EVIDENCE_TOP_K must not exceed AERORAGX_CANDIDATE_TOP_K.")

    return ApiRuntimeSettings(
        mode=mode,
        dense_backend=dense_backend,
        candidate_top_k=candidate_top_k,
        evidence_top_k=evidence_top_k,
    )
