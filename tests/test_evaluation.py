"""Correct metrics and strict fit boundaries."""

import json
import math

import pytest

from evaluate import ranking_metrics, run_evaluation, temporal_split
from recommender import HybridRecommender


def test_metrics_known_answer():
    actual = ranking_metrics(["a", "x", "b"], {"a", "b", "c"}, 3)
    assert actual["hit_rate"] == 1
    assert actual["precision"] == actual["recall"] == pytest.approx(2 / 3)
    assert actual["ndcg"] == pytest.approx((1 + 0.5) / (1 + 1 / math.log2(3) + 0.5))
    # One relevant item: hit rate 1 is distinct from precision .2.
    assert ranking_metrics(["a", "x"], {"a"}, 5)["precision"] == 0.2
    assert ranking_metrics(["x", "y"], {"a"}, 2)["ndcg"] == 0
    with pytest.raises(ValueError):
        ranking_metrics(["a", "a"], {"a"}, 2)


def test_temporal_no_overlap(dataset):
    _, interactions, _ = dataset
    a, b, c = temporal_split(interactions)
    assert a.date.max() < b.date.min() <= b.date.max() < c.date.min()
    assert not set(a.interaction_id) & set(b.interaction_id)
    assert len(a) + len(b) + len(c) == len(interactions)


def test_pipeline_fit_isolated_and_reproducible(dataset, tmp_path, monkeypatch):
    for name, frame in zip(["customers", "interactions", "services"], dataset, strict=True):
        frame.to_csv(tmp_path / f"{name}.csv", index=False)
    fits = []
    original = HybridRecommender.fit

    def spy(self, customers, interactions, services):
        fits.append(interactions.copy())
        return original(self, customers, interactions, services)

    monkeypatch.setattr(HybridRecommender, "fit", spy)
    first = run_evaluation(tmp_path)
    second = run_evaluation(tmp_path)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert len(fits) == 6
    cutoff = first["splits"]["test_start"]
    assert all(frame.date.max() < cutoff for frame in fits)
    assert fits[0].date.max() < first["splits"]["validation_start"]
    assert first["cold"]["content"]["customers"] > 0
    all_ids = set(dataset[0].customer_id)
    excluded = all_ids - set(fits[2].customer_id)
    assert len(excluded) == first["splits"]["cold_customers_reserved"]
    assert all(not excluded & set(frame.customer_id) for frame in fits)
