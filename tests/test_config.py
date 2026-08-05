from pathlib import Path

import pytest

from aeroragx.config import load_config


def test_load_config(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        "project_name: Test RAG\ndata_dir: local-data\n",
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.project_name == "Test RAG"
    assert config.data_dir == Path("local-data")
    assert config.ntrs.base_url == "https://ntrs.nasa.gov/api"


def test_load_config_rejects_non_mapping(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("- invalid\n- root\n", encoding="utf-8")

    with pytest.raises(ValueError, match="YAML mapping"):
        load_config(path)
