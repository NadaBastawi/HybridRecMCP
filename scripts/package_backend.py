"""Build an allowlisted Azure source archive; never include local secrets or models."""

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "main.py",
    "server.py",
    "schemas.py",
    "settings.py",
    "domain.py",
    "data_utils.py",
    "recommender.py",
    "explanations.py",
    "train.py",
    "evaluate.py",
    "requirements.lock",
    "monitoring/__init__.py",
    "monitoring/logger.py",
    "monitoring/drift_detector.py",
    "config/regions.json",
    "data/customers.csv",
    "data/interactions.csv",
    "data/services.csv",
    "data/manifest.json",
    "reports/evaluation.json",
    "scripts/azure_start.sh",
)


def package_backend(destination, root=ROOT):
    with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(root / name, name)
        # Oryx selects this filename; root requirements.txt belongs to Streamlit.
        archive.write(root / "requirements-api.txt", "requirements.txt")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "release.zip")
    package_backend(parser.parse_args().output)
