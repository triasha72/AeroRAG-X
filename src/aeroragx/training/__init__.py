"""Training-data and adaptation utilities for AeroRAG-X."""

from aeroragx.training.dataset import (
    LeakageAuditReport,
    LeakageFinding,
    TrainingEvidence,
    TrainingExample,
    audit_training_leakage,
    load_training_examples,
    normalize_training_text,
    write_training_examples,
)
from aeroragx.training.formatting import (
    FormattedTrainingExample,
    TrainingMessage,
    format_training_example,
    format_training_examples,
)
from aeroragx.training.split import (
    TrainingSplit,
    assert_document_disjoint,
    split_training_examples,
)

__all__ = [
    "FormattedTrainingExample",
    "LeakageAuditReport",
    "LeakageFinding",
    "TrainingEvidence",
    "TrainingExample",
    "TrainingMessage",
    "TrainingSplit",
    "assert_document_disjoint",
    "audit_training_leakage",
    "format_training_example",
    "format_training_examples",
    "load_training_examples",
    "normalize_training_text",
    "split_training_examples",
    "write_training_examples",
]
