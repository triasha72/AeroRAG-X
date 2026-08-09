"""Common interface for dense vector-search backends."""

from typing import Protocol

from aeroragx.retrieval.dense import DenseSearchHit


class DenseSearchBackend(Protocol):
    """Interface implemented by dense retrieval backends."""

    @property
    def document_count(self) -> int:
        """Return the number of indexed chunks."""
        ...

    @property
    def embedding_dimension(self) -> int:
        """Return the embedding dimension."""
        ...

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[DenseSearchHit]:
        """Return ranked dense-search results."""
        ...
