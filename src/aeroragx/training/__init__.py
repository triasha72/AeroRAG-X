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
from aeroragx.training.protected import (
    ProtectedDocumentManifest,
    ProtectedQueryEvidence,
    load_protected_document_manifest,
    write_protected_document_manifest,
)
from aeroragx.training.selection import (
    LoRASourceSelectionManifest,
    SourceDocumentMetadata,
    SourceDocumentSelection,
    SourceSelectionConfig,
    load_source_selection_config,
    load_source_selection_manifest,
    normalize_source_title,
    select_source_documents,
    sha256_file,
    write_source_selection_manifest,
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
    "LoRASourceSelectionManifest",
    "ProtectedDocumentManifest",
    "ProtectedQueryEvidence",
    "SourceDocumentMetadata",
    "SourceDocumentSelection",
    "SourceSelectionConfig",
    "TrainingEvidence",
    "TrainingExample",
    "TrainingMessage",
    "TrainingSplit",
    "assert_document_disjoint",
    "audit_training_leakage",
    "format_training_example",
    "format_training_examples",
    "load_protected_document_manifest",
    "load_source_selection_config",
    "load_source_selection_manifest",
    "load_training_examples",
    "normalize_source_title",
    "normalize_training_text",
    "select_source_documents",
    "sha256_file",
    "split_training_examples",
    "write_protected_document_manifest",
    "write_source_selection_manifest",
    "write_training_examples",
]
