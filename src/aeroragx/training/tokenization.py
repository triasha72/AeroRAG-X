"""Inference-aligned tokenization with assistant-only supervision."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from aeroragx.generation.prompting import (
    ProviderHardeningConfig,
)
from aeroragx.training.dataset import (
    TrainingExample,
)
from aeroragx.training.formatting import (
    format_training_example,
)

_ASSISTANT_SENTINEL = "<<<AERORAGX_ASSISTANT_CONTENT_START_7F9A6B4C>>>"


@dataclass(frozen=True)
class AssistantOnlyTokenization:
    """One tokenized example with prompt tokens masked from loss."""

    input_ids: list[int]
    attention_mask: list[int]
    labels: list[int]

    assistant_start_character: int
    assistant_start_token: int

    @property
    def sequence_tokens(self) -> int:
        """Return total sequence length."""

        return len(self.input_ids)

    @property
    def supervised_tokens(self) -> int:
        """Return number of assistant tokens contributing to loss."""

        return sum(label != -100 for label in self.labels)


def tokenize_assistant_only(
    example: TrainingExample,
    *,
    tokenizer: Any,
    provider_config: ProviderHardeningConfig,
    max_sequence_tokens: int = 4096,
) -> AssistantOnlyTokenization:
    """Tokenize one example while supervising only the assistant response."""

    if not tokenizer.is_fast:
        raise ValueError(
            "Assistant-only tokenization requires a fast tokenizer with offset mappings."
        )

    formatted = format_training_example(
        example,
        provider_config=provider_config,
    )

    messages = [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in formatted.messages
    ]

    if len(messages) != 3:
        raise ValueError("Expected exactly system, user, and assistant messages.")

    if messages[-1]["role"] != "assistant":
        raise ValueError("Final training message must be assistant.")

    full_rendered = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
        enable_thinking=False,
    )

    if not isinstance(
        full_rendered,
        str,
    ):
        raise TypeError("Rendered chat template must be text.")

    if _ASSISTANT_SENTINEL in full_rendered:
        raise ValueError("Assistant sentinel unexpectedly appears in the training example.")

    marker_messages = [dict(message) for message in messages]

    marker_messages[-1] = {
        "role": "assistant",
        "content": _ASSISTANT_SENTINEL,
    }

    marker_rendered = tokenizer.apply_chat_template(
        marker_messages,
        tokenize=False,
        add_generation_prompt=False,
        enable_thinking=False,
    )

    if not isinstance(
        marker_rendered,
        str,
    ):
        raise TypeError("Marker chat template must render to text.")

    marker_count = marker_rendered.count(_ASSISTANT_SENTINEL)

    if marker_count != 1:
        raise ValueError("Assistant sentinel must occur exactly once.")

    assistant_start_character = marker_rendered.index(_ASSISTANT_SENTINEL)

    if marker_rendered[:assistant_start_character] != full_rendered[:assistant_start_character]:
        raise ValueError("Assistant template prefix changed when replacing response content.")

    encoded = tokenizer(
        full_rendered,
        add_special_tokens=False,
        return_attention_mask=True,
        return_offsets_mapping=True,
    )

    input_ids = [int(token_id) for token_id in encoded["input_ids"]]

    attention_mask = [int(value) for value in encoded["attention_mask"]]

    offsets = [
        (
            int(start),
            int(end),
        )
        for start, end in encoded["offset_mapping"]
    ]

    canonical_output = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=False,
        enable_thinking=False,
        return_dict=False,
    )

    if isinstance(
        canonical_output,
        Mapping,
    ):
        if "input_ids" not in canonical_output:
            raise ValueError("Chat-template output mapping does not contain input_ids.")

        canonical_input_ids = canonical_output["input_ids"]

    else:
        canonical_input_ids = canonical_output

    if hasattr(
        canonical_input_ids,
        "tolist",
    ):
        canonical_input_ids = canonical_input_ids.tolist()

    if (
        isinstance(
            canonical_input_ids,
            list,
        )
        and canonical_input_ids
        and isinstance(
            canonical_input_ids[0],
            list,
        )
    ):
        if len(canonical_input_ids) != 1:
            raise ValueError("Unexpected batched chat-template output.")

        canonical_input_ids = canonical_input_ids[0]

    if not isinstance(
        canonical_input_ids,
        list,
    ):
        raise TypeError("Chat-template input_ids must resolve to a list.")

    canonical_ids = [int(token_id) for token_id in canonical_input_ids]

    if input_ids != canonical_ids:
        raise ValueError(
            "Rendered-then-tokenized sequence does not match canonical chat-template tokenization."
        )

    if len(input_ids) != len(offsets):
        raise ValueError("Token IDs and offset mappings differ in length.")

    if len(input_ids) != len(attention_mask):
        raise ValueError("Token IDs and attention mask differ in length.")

    assistant_start_token: int | None = None

    for index, (
        _,
        end,
    ) in enumerate(offsets):
        if end > assistant_start_character:
            assistant_start_token = index
            break

    if assistant_start_token is None:
        raise ValueError("Could not locate the first assistant content token.")

    labels = [-100] * assistant_start_token + input_ids[assistant_start_token:]

    if len(input_ids) > max_sequence_tokens:
        raise ValueError(
            f"{example.example_id}: sequence contains "
            f"{len(input_ids)} tokens, exceeding "
            f"the {max_sequence_tokens}-token limit."
        )

    supervised_tokens = sum(label != -100 for label in labels)

    if supervised_tokens <= 0:
        raise ValueError(f"{example.example_id}: no assistant tokens are supervised.")

    return AssistantOnlyTokenization(
        input_ids=input_ids,
        attention_mask=attention_mask,
        labels=labels,
        assistant_start_character=(assistant_start_character),
        assistant_start_token=(assistant_start_token),
    )
