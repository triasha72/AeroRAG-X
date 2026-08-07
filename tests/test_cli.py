from click import Command
from typer.core import TyperGroup
from typer.main import get_command
from typer.testing import CliRunner

from aeroragx.cli import app

runner = CliRunner()


def get_subcommand(command_name: str) -> Command:
    """Return a registered AeroRAG-X subcommand."""

    root_command = get_command(app)

    assert isinstance(root_command, TyperGroup)
    assert command_name in root_command.commands

    return root_command.commands[command_name]


def option_names(command_name: str) -> set[str]:
    """Return the internal option names for a command."""

    command = get_subcommand(command_name)

    return {parameter.name for parameter in command.params if parameter.name is not None}


def test_info_command() -> None:
    result = runner.invoke(
        app,
        ["info"],
        color=False,
    )

    assert result.exit_code == 0
    assert "AeroRAG-X 0.1.0" in result.stdout


def test_expected_commands_are_registered() -> None:
    root_command = get_command(app)

    assert isinstance(root_command, TyperGroup)

    expected_commands = {
        "info",
        "validate-config",
        "ntrs-search",
        "ntrs-build-manifest",
        "ntrs-download-documents",
        "ntrs-extract-pages",
        "ntrs-build-chunks",
        "ntrs-bm25-search",
        "ntrs-build-dense-index",
        "ntrs-dense-search",
        "ntrs-hybrid-search",
        "ntrs-reranker-search",
        "ntrs-grounded-answer",
        "ntrs-evaluate-generation",
        "ntrs-build-evaluation-candidates",
        "ntrs-evaluate-bm25",
        "ntrs-evaluate-dense",
        "ntrs-evaluate-hybrid",
        "ntrs-evaluate-reranker",
        "ntrs-build-pooled-candidates",
        "ntrs-build-qrels-from-annotations",
    }

    assert expected_commands <= set(root_command.commands)


def test_build_manifest_options_are_registered() -> None:
    names = option_names("ntrs-build-manifest")

    assert {
        "corpus_config",
        "output",
        "config",
    } <= names


def test_download_options_are_registered() -> None:
    names = option_names("ntrs-download-documents")

    assert {
        "manifest",
        "documents_dir",
        "receipts_output",
        "limit",
        "overwrite",
        "config",
    } <= names


def test_extract_pages_options_are_registered() -> None:
    names = option_names("ntrs-extract-pages")

    assert {
        "receipts_input",
        "pages_output",
        "extraction_output",
        "limit",
        "max_size_mb",
    } <= names


def test_build_chunks_options_are_registered() -> None:
    names = option_names("ntrs-build-chunks")

    assert {
        "pages_input",
        "chunking_config",
        "chunks_output",
        "receipts_output",
    } <= names


def test_bm25_search_options_are_registered() -> None:
    names = option_names("ntrs-bm25-search")

    assert {
        "query",
        "chunks_input",
        "bm25_config",
        "top_k",
        "output",
    } <= names


def test_evaluation_candidate_options() -> None:
    names = option_names("ntrs-build-evaluation-candidates")

    assert {
        "queries_input",
        "chunks_input",
        "bm25_config",
        "top_k",
        "output",
    } <= names


def test_evaluate_bm25_options() -> None:
    names = option_names("ntrs-evaluate-bm25")

    assert {
        "queries_input",
        "qrels_input",
        "chunks_input",
        "bm25_config",
        "top_k",
        "report_output",
    } <= names


def test_build_dense_index_options() -> None:
    names = option_names("ntrs-build-dense-index")

    assert {
        "chunks_input",
        "dense_config",
        "embeddings_output",
        "metadata_output",
        "manifest_output",
    } <= names


def test_dense_search_options() -> None:
    names = option_names("ntrs-dense-search")

    assert {
        "query",
        "dense_config",
        "embeddings_input",
        "metadata_input",
        "manifest_input",
        "top_k",
        "output",
    } <= names


def test_evaluate_dense_options() -> None:
    names = option_names("ntrs-evaluate-dense")

    assert {
        "queries_input",
        "qrels_input",
        "dense_config",
        "embeddings_input",
        "metadata_input",
        "manifest_input",
        "top_k",
        "report_output",
    } <= names


def test_hybrid_search_options() -> None:
    names = option_names("ntrs-hybrid-search")

    assert {
        "query",
        "chunks_input",
        "bm25_config",
        "dense_config",
        "hybrid_config",
        "embeddings_input",
        "metadata_input",
        "manifest_input",
        "top_k",
        "output",
    } <= names


def test_evaluate_hybrid_options() -> None:
    names = option_names("ntrs-evaluate-hybrid")

    assert {
        "queries_input",
        "qrels_input",
        "chunks_input",
        "bm25_config",
        "dense_config",
        "hybrid_config",
        "embeddings_input",
        "metadata_input",
        "manifest_input",
        "top_k",
        "report_output",
    } <= names


def test_reranker_search_options() -> None:
    names = option_names("ntrs-reranker-search")

    assert {
        "query",
        "chunks_input",
        "bm25_config",
        "dense_config",
        "hybrid_config",
        "reranker_config",
        "embeddings_input",
        "metadata_input",
        "manifest_input",
        "candidate_top_k",
        "top_k",
        "output",
    } <= names


def test_evaluate_reranker_options() -> None:
    names = option_names("ntrs-evaluate-reranker")

    assert {
        "queries_input",
        "qrels_input",
        "chunks_input",
        "bm25_config",
        "dense_config",
        "hybrid_config",
        "reranker_config",
        "embeddings_input",
        "metadata_input",
        "manifest_input",
        "candidate_top_k",
        "top_k",
        "report_output",
        "latency_output",
        "hardware_note",
    } <= names


def test_grounded_answer_options() -> None:
    names = option_names("ntrs-grounded-answer")

    assert {
        "query",
        "chunks_input",
        "bm25_config",
        "dense_config",
        "hybrid_config",
        "reranker_config",
        "generation_config",
        "sufficiency_config",
        "embeddings_input",
        "metadata_input",
        "manifest_input",
        "candidate_top_k",
        "evidence_top_k",
        "output",
    } <= names


def test_evaluate_generation_options() -> None:
    names = option_names("ntrs-evaluate-generation")

    assert {
        "queries_input",
        "chunks_input",
        "bm25_config",
        "dense_config",
        "hybrid_config",
        "reranker_config",
        "generation_config",
        "sufficiency_config",
        "embeddings_input",
        "metadata_input",
        "manifest_input",
        "candidate_top_k",
        "evidence_top_k",
        "report_output",
    } <= names


def test_build_pooled_candidates_options() -> None:
    names = option_names("ntrs-build-pooled-candidates")

    assert {
        "queries_input",
        "previous_qrels_input",
        "chunks_input",
        "bm25_config",
        "dense_config",
        "embeddings_input",
        "metadata_input",
        "manifest_input",
        "top_k_per_retriever",
        "shuffle_seed",
        "internal_output",
        "annotation_output",
    } <= names


def test_build_qrels_from_annotations_options() -> None:
    names = option_names("ntrs-build-qrels-from-annotations")

    assert {
        "annotations_input",
        "output",
    } <= names
