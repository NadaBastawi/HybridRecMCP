"""Regression coverage for private artifact preparation and safe recovery."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

import model_store
from domain import ROOT
from train import artifact_metadata, validated_selection


@pytest.fixture
def prepared(tmp_path, monkeypatch, engine):
    calls = []

    def train():
        calls.append(1)
        return engine

    monkeypatch.setattr(model_store, "train_from_data", train)
    return tmp_path, calls


def test_fresh_and_warm_preparation(prepared, monkeypatch):
    cache, calls = prepared
    first = model_store.prepare_demo_model(cache)
    assert first.recommend("C0001")
    before = (cache / "model.pkl").stat().st_mtime_ns
    second = model_store.prepare_demo_model(cache)
    assert second.recommend("C0001") == first.recommend("C0001")
    assert len(calls) == 1 and (cache / "model.pkl").stat().st_mtime_ns == before


@pytest.mark.parametrize(
    "fault", ["missing_manifest", "stale_metadata", "corrupt_bytes", "unknown_origin"]
)
def test_invalid_cache_rebuilt_without_loading(prepared, monkeypatch, fault):
    cache, calls = prepared
    model_store.prepare_demo_model(cache)
    manifest = cache / "manifest.json"
    record = json.loads(manifest.read_text())
    if fault == "missing_manifest":
        manifest.unlink()
    elif fault == "stale_metadata":
        record["metadata"]["python"] = "0.0"
        manifest.write_text(json.dumps(record))
    elif fault == "unknown_origin":
        record["origin"] = "uploaded"
        manifest.write_text(json.dumps(record))
    else:
        (cache / "model.pkl").write_bytes(b"not a model")

    loads = []

    def forbidden_load(*args, **kwargs):
        loads.append(1)
        raise AssertionError("Unverified serialized bytes must not be loaded")

    monkeypatch.setattr(model_store.HybridRecommender, "load", forbidden_load)
    assert model_store.prepare_demo_model(cache)
    assert len(calls) == 2 and not loads


def test_unknown_pickle_is_never_deserialized(prepared, monkeypatch):
    cache, calls = prepared
    (cache / "model.pkl").write_bytes(b"arbitrary uploaded pickle bytes")
    assert model_store.prepare_demo_model(cache)
    assert len(calls) == 1


def test_concurrent_preparation_trains_once(prepared):
    cache, calls = prepared
    with ThreadPoolExecutor(max_workers=4) as pool:
        models = list(pool.map(lambda _: model_store.prepare_demo_model(cache), range(4)))
    assert len(calls) == 1
    assert all(model.recommend("C0001") == models[0].recommend("C0001") for model in models)


def test_report_compatibility_rejected(tmp_path):
    report = json.loads((ROOT / "reports/evaluation.json").read_text())
    report["data_fingerprint"] = "different-data"
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="different data"):
        validated_selection(ROOT / "data", path)


def test_cache_manifest_matches_current_metadata(prepared):
    cache, _ = prepared
    model_store.prepare_demo_model(cache)
    record = json.loads((cache / "manifest.json").read_text())
    assert record["metadata"] == artifact_metadata(ROOT / "data")
    assert record["sha256"] == hashlib.sha256((cache / "model.pkl").read_bytes()).hexdigest()
