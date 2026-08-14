"""Tests for Phase 38 human-review contracts."""

import pytest
from pydantic import ValidationError

from aeroragx.agent.human_review import HumanReviewResponse


def test_edit_requires_edited_query() -> None:
    with pytest.raises(ValidationError, match="edited_query"):
        HumanReviewResponse(
            review_id="review-1",
            decision="edit",
            rationale="Clarify the query.",
        )
