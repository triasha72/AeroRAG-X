"""Tests for optional PEFT adapter loading in the Transformers transport."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import Any, ClassVar

import pytest
import torch

from aeroragx.generation.transformers_transport import (
    TransformersRuntimeConfig,
    _load_transformers_components,
    _resolve_adapter_path,
)


def make_config(
    *,
    adapter_path: Path | None = None,
) -> TransformersRuntimeConfig:
    """Build one deterministic CPU runtime configuration."""

    return TransformersRuntimeConfig(
        version="0.1",
        device="cpu",
        dtype="float32",
        context_window_tokens=1024,
        max_input_tokens=512,
        max_new_tokens=64,
        do_sample=False,
        temperature=0.7,
        top_p=0.8,
        top_k=20,
        enable_thinking=False,
        trust_remote_code=False,
        local_files_only=True,
        revision=None,
        adapter_path=adapter_path,
    )


def test_adapter_path_is_optional() -> None:
    """Base-model inference should not require an adapter."""

    assert _resolve_adapter_path(make_config()) is None


def test_missing_adapter_directory_is_rejected(
    tmp_path: Path,
) -> None:
    """A configured adapter path must exist."""

    missing = tmp_path / "missing-adapter"

    with pytest.raises(
        ValueError,
        match=("does not exist or is not a directory"),
    ):
        _resolve_adapter_path(
            make_config(
                adapter_path=missing,
            )
        )


def test_adapter_directory_requires_adapter_config(
    tmp_path: Path,
) -> None:
    """A configured adapter directory must look like a PEFT checkpoint."""

    adapter_dir = tmp_path / "adapter"

    adapter_dir.mkdir()

    with pytest.raises(
        ValueError,
        match=r"missing adapter_config\.json",
    ):
        _resolve_adapter_path(
            make_config(
                adapter_path=adapter_dir,
            )
        )


def test_load_components_applies_peft_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Loading with adapter_path should wrap the base model with PEFT."""

    adapter_dir = tmp_path / "adapter"

    adapter_dir.mkdir()

    (adapter_dir / "adapter_config.json").write_text(
        "{}",
        encoding="utf-8",
    )

    class FakeTokenizer:
        """Minimal tokenizer object."""

    class FakeModel:
        """Minimal causal model supporting device placement and eval."""

        def __init__(self) -> None:
            self.device: torch.device | None = None

            self.eval_called = False

        def to(
            self,
            device: torch.device,
        ) -> FakeModel:
            self.device = device

            return self

        def eval(
            self,
        ) -> FakeModel:
            self.eval_called = True

            return self

    class FakeAutoTokenizer:
        """Fake AutoTokenizer entry point."""

        @classmethod
        def from_pretrained(
            cls,
            model_name: str,
            **kwargs: Any,
        ) -> FakeTokenizer:
            return FakeTokenizer()

    class FakeAutoModelForCausalLM:
        """Fake AutoModelForCausalLM entry point."""

        @classmethod
        def from_pretrained(
            cls,
            model_name: str,
            **kwargs: Any,
        ) -> FakeModel:
            return FakeModel()

    class FakePeftModel:
        """Fake PEFT wrapper recording adapter-loading arguments."""

        adapter_path: ClassVar[str | None] = None

        is_trainable: ClassVar[bool | None] = None

        @classmethod
        def from_pretrained(
            cls,
            model: FakeModel,
            adapter_path: str,
            *,
            is_trainable: bool,
        ) -> FakeModel:
            cls.adapter_path = adapter_path

            cls.is_trainable = is_trainable

            return model

    transformers_module = ModuleType("transformers")

    transformers_module.__dict__["AutoTokenizer"] = FakeAutoTokenizer

    transformers_module.__dict__["AutoModelForCausalLM"] = FakeAutoModelForCausalLM

    peft_module = ModuleType("peft")

    peft_module.__dict__["PeftModel"] = FakePeftModel

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        transformers_module,
    )

    monkeypatch.setitem(
        sys.modules,
        "peft",
        peft_module,
    )

    (
        tokenizer,
        model,
        device,
    ) = _load_transformers_components(
        model_name="test-model",
        config=make_config(
            adapter_path=adapter_dir,
        ),
    )

    assert isinstance(
        tokenizer,
        FakeTokenizer,
    )

    assert isinstance(
        model,
        FakeModel,
    )

    assert device == torch.device("cpu")

    assert model.device == torch.device("cpu")

    assert model.eval_called is True

    assert FakePeftModel.adapter_path == str(adapter_dir)

    assert FakePeftModel.is_trainable is False
