from typer.testing import CliRunner

from aeroragx.cli import app

runner = CliRunner()


def test_info_command() -> None:
    result = runner.invoke(app, ["info"])

    assert result.exit_code == 0
    assert "AeroRAG-X 0.1.0" in result.stdout


def test_build_manifest_command_is_registered() -> None:
    result = runner.invoke(
        app,
        ["ntrs-build-manifest", "--help"],
    )

    assert result.exit_code == 0
    assert "corpus-config" in result.stdout
    assert "output" in result.stdout


def test_download_documents_command_is_registered() -> None:
    result = runner.invoke(
        app,
        ["ntrs-download-documents", "--help"],
    )

    assert result.exit_code == 0
    assert "manifest" in result.stdout
    assert "documents-dir" in result.stdout
    assert "receipts-output" in result.stdout
