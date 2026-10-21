"""Deployment boundaries: host-selected dependencies and secret-free API packaging."""

from zipfile import ZipFile

from domain import ROOT
from scripts.package_backend import FILES, package_backend


def test_backend_archive_is_explicit_and_api_only(tmp_path):
    archive = tmp_path / "release.zip"
    package_backend(archive)
    with ZipFile(archive) as bundle:
        assert set(bundle.namelist()) == set(FILES) | {"requirements.txt"}
        assert bundle.read("requirements.txt") == (ROOT / "requirements-api.txt").read_bytes()
        assert b"requirements.lock" in bundle.read("requirements.txt")
        assert not any(
            name.endswith((".pkl", ".env", "secrets.toml")) or name.startswith((".git/", ".cache/"))
            for name in bundle.namelist()
        )


def test_root_cloud_requirements_select_demo_lock():
    assert "-r requirements-demo.lock" in (ROOT / "requirements.txt").read_text()
    assert "127.0.0.1" not in (ROOT / ".streamlit/config.toml").read_text()
    assert 'showErrorDetails = "none"' in (ROOT / ".streamlit/config.toml").read_text()
