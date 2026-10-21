"""Train a trusted, versioned local artifact; never trains at API import/startup."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

from data_utils import data_fingerprint, load_data
from domain import ROOT
from evaluate import fit_model


def artifact_metadata(data_dir, evaluation_path=ROOT / "reports/evaluation.json"):
    return dict(
        data_fingerprint=data_fingerprint(data_dir),
        python=platform.python_version(),
        packages={
            p: importlib.metadata.version(p) for p in ("numpy", "pandas", "scikit-learn", "joblib")
        },
        implementation_hash=hashlib.sha256(
            b"".join(
                (ROOT / name).read_bytes()
                for name in ("recommender.py", "domain.py", "explanations.py", "train.py")
            )
        ).hexdigest(),
        evaluation_hash=hashlib.sha256(Path(evaluation_path).read_bytes()).hexdigest(),
    )


def validated_selection(data_dir, evaluation_path):
    """Reuse measured validation choices without running evaluation during startup."""
    report = json.loads(Path(evaluation_path).read_text(encoding="utf-8"))
    if report.get("schema_version") != 2 or report.get("synthetic_data") is not True:
        raise ValueError("A compatible synthetic evaluation report is required")
    if report["data_fingerprint"] != data_fingerprint(data_dir):
        raise ValueError("Evaluation uses different data; rerun evaluate.py")
    selected = report["selected"]
    cb, cf, rank = selected["cb_weight"], selected["cf_weight"], selected["svd_components"]
    if not (0 <= cb <= 1 and 0 <= cf <= 1 and abs(cb + cf - 1) < 1e-9):
        raise ValueError("Invalid evaluated weights")
    if isinstance(rank, bool) or not isinstance(rank, int) or not 1 <= rank <= 9:
        raise ValueError("Invalid evaluated SVD rank")
    return selected


def train_from_data(data_dir=ROOT / "data", evaluation_path=ROOT / "reports/evaluation.json"):
    selected = validated_selection(data_dir, evaluation_path)
    customers, interactions, services = load_data(data_dir)
    return fit_model(
        customers, interactions, services, selected["cb_weight"], selected["svd_components"]
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--model-dir", type=Path, default=ROOT / "models")
    parser.add_argument("--evaluation", type=Path, default=ROOT / "reports/evaluation.json")
    args = parser.parse_args()
    model = train_from_data(args.data_dir, args.evaluation)
    path = args.model_dir / "torco_recommender.pkl"
    model.save(path, artifact_metadata(args.data_dir, args.evaluation))
    print(f"Saved trusted demo artifact: {path}")


if __name__ == "__main__":
    main()
