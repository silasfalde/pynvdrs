from pynvdrs.paths import data_dir, data_paths, project_root, root_path


def test_project_root_finds_marker(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    nested = tmp_path / "src" / "pkg"
    nested.mkdir(parents=True)

    assert project_root(nested) == tmp_path


def test_data_dir_and_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "custom-data"))

    assert data_dir(project_root=tmp_path) == tmp_path / "custom-data"
    assert root_path("data", project_root=tmp_path) == tmp_path / "data"


def test_data_paths_uses_prefix(tmp_path, monkeypatch):
    monkeypatch.setenv("NVDRS_DATA_DIR", str(tmp_path / "dataset"))

    paths = data_paths(prefix="NVDRS", project_root=tmp_path)

    assert paths["DATA_DIR"] == tmp_path / "dataset"
    assert paths["RAW_DIR"] == tmp_path / "dataset" / "raw"
