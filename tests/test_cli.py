from typer.testing import CliRunner

from aeroragx.cli import app

runner = CliRunner()


def test_info_command() -> None:
    result = runner.invoke(app, ["info"])

    assert result.exit_code == 0
    assert "AeroRAG-X 0.1.0" in result.stdout
