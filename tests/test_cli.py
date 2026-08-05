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
