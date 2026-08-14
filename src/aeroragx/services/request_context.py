"""Cross-service request identity contracts."""

from pydantic import BaseModel, ConfigDict, Field


class RequestContext(BaseModel):
    """IDs that must propagate across service boundaries."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
