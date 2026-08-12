#!/usr/bin/env python3
"""Run the protected Phase 26 paired adaptive-retrieval evaluation once."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from aeroragx.generation.adaptive_evaluation import (
    AdaptiveRetrievalEvaluationConfig,
    evaluate_adaptive_retrieval,
    load_adaptive_retrieval_evaluation_config,
    write_adaptive_retrieval_condition_report,
    write_adaptive_retrieval_evaluation_markdown,
    write_adaptive_retrieval_evaluation_report,
)
from aeroragx.generation.evaluation import load_generation_evaluation_queries
from aeroragx.runtime import AeroRAGRuntime, RuntimeConfig, load_grounded_runtime

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    """Parse the explicit Phase 26 execution controls."""

    parser = argparse.ArgumentParser(
        description=("Run one protected comparison of single-pass and bounded adaptive retrieval.")
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/adaptive_retrieval_evaluation_v0_1.yaml"),
        help="Frozen Phase 26 evaluation protocol.",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Permit replacing existing Phase 26 output artifacts.",
    )

    return parser.parse_args()


def main() -> None:
    """Execute the paired study and write its immutable outputs."""

    args = parse_args()
    settings = load_adaptive_retrieval_evaluation_config(
        _from_root(args.config),
    )

    output_paths = [
        _from_root(settings.inputs_output),
        _from_root(settings.baseline_output),
        _from_root(settings.adaptive_output),
        _from_root(settings.comparison_output),
        _from_root(settings.report_output),
    ]

    _validate_output_paths(
        output_paths,
        overwrite=args.overwrite,
    )
    _validate_frozen_inputs(settings)
    _validate_pinned_input_hashes(settings)
    _validate_phase25_baseline_manifest(settings)

    checksum_manifest = _render_checksum_manifest(
        input_paths=[_from_root(path) for path in settings.frozen_inputs],
    )

    queries = load_generation_evaluation_queries(
        _from_root(settings.queries_input),
    )
    protected_baseline = _load_json_object(
        _from_root(settings.protected_baseline_report),
    )

    single_pass_runtime = load_grounded_runtime(
        _runtime_config(
            settings,
            adaptive_retrieval_config=None,
        )
    )
    bounded_adaptive_runtime = load_grounded_runtime(
        _runtime_config(
            settings,
            adaptive_retrieval_config=_from_root(settings.adaptive_retrieval_config),
        )
    )

    _validate_runtime_parity(
        settings=settings,
        single_pass_runtime=single_pass_runtime,
        bounded_adaptive_runtime=bounded_adaptive_runtime,
    )

    comparison = evaluate_adaptive_retrieval(
        single_pass_generator=single_pass_runtime.generator,
        bounded_adaptive_generator=bounded_adaptive_runtime.generator,
        queries=queries,
        generation_provider=single_pass_runtime.generation_settings.provider,
        generation_model=single_pass_runtime.generation_settings.model_name,
        protected_baseline=protected_baseline,
        config=settings,
        reranker_model=single_pass_runtime.reranker_settings.model_name,
    )

    _write_text(
        _from_root(settings.inputs_output),
        checksum_manifest,
    )
    write_adaptive_retrieval_condition_report(
        _from_root(settings.baseline_output),
        comparison.single_pass,
    )
    write_adaptive_retrieval_condition_report(
        _from_root(settings.adaptive_output),
        comparison.bounded_adaptive,
    )
    write_adaptive_retrieval_evaluation_report(
        _from_root(settings.comparison_output),
        comparison,
    )
    write_adaptive_retrieval_evaluation_markdown(
        _from_root(settings.report_output),
        comparison,
    )

    print("Phase 26 bounded adaptive-retrieval evaluation")
    print("----------------------------------------------")
    print("Queries:", comparison.single_pass.generation_report.query_count)
    print("Protected baseline parity:", comparison.protected_baseline_parity.matched)
    print("Recovery triggers:", comparison.bounded_adaptive.recovery_trigger_count)
    print("Successful recoveries:", comparison.bounded_adaptive.successful_recovery_count)
    print("Verdict:", comparison.verdict)
    print("Comparison artifact:", settings.comparison_output)
    print("Markdown report:", settings.report_output)

    if comparison.verdict in {
        "baseline_parity_failed",
        "integrity_regression",
        "quality_regression",
    }:
        raise SystemExit(
            "Phase 26 wrote the diagnostic artifacts but the result requires investigation."
        )


def _runtime_config(
    settings: AdaptiveRetrievalEvaluationConfig,
    *,
    adaptive_retrieval_config: Path | None,
) -> RuntimeConfig:
    """Build one fair runtime from the frozen Phase 26 protocol."""

    return RuntimeConfig(
        chunks_input=_from_root(settings.chunks_input),
        bm25_config=_from_root(settings.bm25_config),
        dense_config=_from_root(settings.dense_config),
        hybrid_config=_from_root(settings.hybrid_config),
        reranker_config=_from_root(settings.reranker_config),
        generation_config=_from_root(settings.generation_config),
        sufficiency_config=_from_root(settings.sufficiency_config),
        facet_retrieval_config=(
            _from_root(settings.facet_retrieval_config)
            if settings.facet_retrieval_config is not None
            else None
        ),
        adaptive_retrieval_config=adaptive_retrieval_config,
        embeddings_input=_from_root(settings.embeddings_input),
        metadata_input=_from_root(settings.metadata_input),
        manifest_input=_from_root(settings.manifest_input),
        candidate_top_k=settings.candidate_top_k,
        evidence_top_k=settings.evidence_top_k,
    )


def _validate_runtime_parity(
    *,
    settings: AdaptiveRetrievalEvaluationConfig,
    single_pass_runtime: AeroRAGRuntime,
    bounded_adaptive_runtime: AeroRAGRuntime,
) -> None:
    """Reject an accidental model or retrieval difference between conditions."""

    if single_pass_runtime.generation_settings != bounded_adaptive_runtime.generation_settings:
        raise RuntimeError("The two Phase 26 conditions loaded different generation settings.")

    if single_pass_runtime.reranker_settings != bounded_adaptive_runtime.reranker_settings:
        raise RuntimeError("The two Phase 26 conditions loaded different reranker settings.")

    if single_pass_runtime.generation_settings.evidence_top_k != settings.evidence_top_k:
        raise RuntimeError("Runtime evidence_top_k differs from the frozen Phase 26 protocol.")

    if single_pass_runtime.reranker_settings.candidate_top_k != settings.candidate_top_k:
        raise RuntimeError("Runtime candidate_top_k differs from the frozen Phase 26 protocol.")

    if single_pass_runtime.generator.adaptive_retrieval_config is not None:
        raise RuntimeError("The Phase 26 single-pass runtime unexpectedly enabled recovery.")

    adaptive_policy = bounded_adaptive_runtime.generator.adaptive_retrieval_config

    if adaptive_policy is None:
        raise RuntimeError("The Phase 26 bounded-adaptive runtime did not enable recovery.")

    if adaptive_policy.maximum_retrieval_passes != settings.maximum_retrieval_passes:
        raise RuntimeError(
            "Adaptive retrieval-pass bound differs from the frozen Phase 26 protocol."
        )

    if adaptive_policy.maximum_query_rewrites != settings.maximum_query_rewrites:
        raise RuntimeError("Adaptive rewrite bound differs from the frozen Phase 26 protocol.")


def _validate_frozen_inputs(
    settings: AdaptiveRetrievalEvaluationConfig,
) -> None:
    """Fail before the run if any declared frozen input is missing."""

    missing_paths = [
        _from_root(path) for path in settings.frozen_inputs if not _from_root(path).is_file()
    ]

    if missing_paths:
        formatted = ", ".join(str(path) for path in missing_paths)
        raise FileNotFoundError(f"Phase 26 frozen input is missing: {formatted}")


def _validate_pinned_input_hashes(
    settings: AdaptiveRetrievalEvaluationConfig,
) -> None:
    """Reject a changed evaluation input before protected queries are run."""

    mismatches = [
        (
            path,
            expected_digest,
            _sha256(_from_root(path)),
        )
        for path, expected_digest in settings.pinned_input_sha256.items()
        if _sha256(_from_root(path)) != expected_digest
    ]

    if mismatches:
        formatted = ", ".join(
            f"{path} (expected {expected}, observed {observed})"
            for path, expected, observed in mismatches
        )
        raise RuntimeError(f"A pinned Phase 26 input changed: {formatted}")


def _validate_phase25_baseline_manifest(
    settings: AdaptiveRetrievalEvaluationConfig,
) -> None:
    """Verify the frozen Phase 25 input contract before evaluating it again."""

    manifest_path = _from_root(settings.phase25_baseline_manifest)
    manifest = _load_json_object(manifest_path)

    if manifest.get("phase") != 25:
        raise ValueError("Phase 26 requires a Phase 25 baseline manifest.")

    manifest_inputs = manifest.get("frozen_inputs")

    if not isinstance(manifest_inputs, list):
        raise ValueError("Phase 25 baseline manifest has no frozen_inputs list.")

    expected_by_path: dict[Path, str] = {}

    for index, item in enumerate(manifest_inputs):
        if not isinstance(item, Mapping):
            raise ValueError(f"Phase 25 manifest input {index} is not an object.")

        raw_path = item.get("path")
        raw_digest = item.get("sha256")

        if not isinstance(raw_path, str) or not isinstance(raw_digest, str):
            raise ValueError(f"Phase 25 manifest input {index} is incomplete.")

        expected_by_path[Path(raw_path)] = raw_digest

    required_paths = {
        settings.protected_baseline_report,
        settings.generation_config,
        settings.sufficiency_config,
        settings.hybrid_config,
        settings.reranker_config,
    }
    missing_paths = required_paths - set(expected_by_path)

    if missing_paths:
        formatted = ", ".join(str(path) for path in sorted(missing_paths))
        raise ValueError(f"Phase 25 manifest is missing protected inputs: {formatted}")

    mismatches = [
        (
            path,
            expected_digest,
            _sha256(_from_root(path)),
        )
        for path, expected_digest in expected_by_path.items()
        if _sha256(_from_root(path)) != expected_digest
    ]

    if mismatches:
        formatted = ", ".join(
            f"{path} (expected {expected}, observed {observed})"
            for path, expected, observed in mismatches
        )
        raise RuntimeError(f"The Phase 25 protected baseline changed: {formatted}")


def _validate_output_paths(
    paths: list[Path],
    *,
    overwrite: bool,
) -> None:
    """Prevent accidental replacement of a completed held-out evaluation."""

    existing_paths = [path for path in paths if path.exists()]

    if existing_paths and not overwrite:
        formatted = ", ".join(str(path) for path in existing_paths)
        raise FileExistsError(
            "Phase 26 output already exists. Refusing to overwrite: "
            f"{formatted}. Use --overwrite only for an intentional replacement."
        )


def _render_checksum_manifest(
    *,
    input_paths: list[Path],
) -> str:
    """Render conventional SHA-256 lines for every frozen Phase 26 input."""

    lines = [f"{_sha256(input_path)}  {_display_path(input_path)}" for input_path in input_paths]

    return "\n".join(lines) + "\n"


def _write_text(
    path: Path,
    value: str,
) -> None:
    """Write one UTF-8 text artifact, creating its parent directory if needed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _sha256(path: Path) -> str:
    """Calculate one file checksum without loading a large artifact at once."""

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)

    return digest.hexdigest()


def _load_json_object(
    path: Path,
) -> dict[str, object]:
    """Load one protected JSON object."""

    value = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(value, dict):
        raise TypeError(f"Protected baseline must be a JSON object: {path}")

    return value


def _from_root(path: Path) -> Path:
    """Resolve a configured repository-relative path safely."""

    return path if path.is_absolute() else ROOT / path


def _display_path(path: Path) -> str:
    """Use repository-relative paths in portable checksum artifacts."""

    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
