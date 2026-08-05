from click.testing import Result
from typer.testing import CliRunner

from aeroragx.cli import app

runner = CliRunner()


def invoke_help(command: str) -> Result:
    """Invoke command help using a deterministic terminal width."""

    return runner.invoke(
        app,
        [command, "--help"],
        color=False,
        terminal_width=240,
    )


def test_info_command() -> None:
    result = runner.invoke(
        app,
        ["info"],
        color=False,
        terminal_width=240,
    )

    assert result.exit_code == 0
    assert "AeroRAG-X 0.1.0" in result.stdout


def test_build_manifest_command_is_registered() -> None:
    result = invoke_help("ntrs-build-manifest")

    assert result.exit_code == 0
    assert "--corpus-config" in result.stdout
    assert "--output" in result.stdout


def test_download_documents_command_is_registered() -> None:
    result = invoke_help("ntrs-download-documents")

    assert result.exit_code == 0
    assert "--manifest" in result.stdout
    assert "--documents-dir" in result.stdout
    assert "--receipts-output" in result.stdout


def test_extract_pages_command_is_registered() -> None:
    result = invoke_help("ntrs-extract-pages")

    assert result.exit_code == 0
    assert "--receipts-input" in result.stdout
    assert "--pages-output" in result.stdout
    assert "--max-size-mb" in result.stdout
