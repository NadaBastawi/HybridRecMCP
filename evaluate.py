"""Leakage-free temporal ranking and customer-disjoint cold-start evaluation."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from data_utils import data_fingerprint, load_data
from domain import ROOT, rule_urgency, season_for_month
from recommender import HybridRecommender


def temporal_split(interactions):
    dates = pd.to_datetime(interactions.date)
    boundaries = sorted(dates.unique())
    if len(boundaries) < 5:
        raise ValueError("At least five different dates required")
    first = boundaries[int(len(boundaries) * 0.6)]
    second = boundaries[int(len(boundaries) * 0.8)]
    return tuple(
        interactions.loc[mask].copy()
        for mask in (dates < first, (dates >= first) & (dates < second), dates >= second)
    )


def ranking_metrics(recommended, relevant, k):
    if k < 1 or not relevant or len(recommended) != len(set(recommended)):
        raise ValueError("Positive K, relevant items and unique recommendations required")
    hits = [int(sid in relevant) for sid in recommended[:k]]
    count = sum(hits)
    dcg = sum(hit / math.log2(i + 2) for i, hit in enumerate(hits))
    ideal = sum(1 / math.log2(i + 2) for i in range(min(k, len(relevant))))
    return {
        "hit_rate": float(count > 0),
        "precision": count / k,
        "recall": count / len(relevant),
        "ndcg": dcg / ideal,
    }


def evaluate_ranking(
    model, history, future, customers, method="hybrid", k=5, cold=False, query_date=None
):
    profiles = customers.set_index("customer_id").to_dict("index")
    # One frozen query per customer at the global start of the future window.
    if future.empty:
        raise ValueError("No future interactions available for evaluation")
    as_of = pd.Timestamp(query_date or future.date.min())
    if pd.Timestamp(history.date.max()) >= as_of:
        raise ValueError("Training history overlaps the evaluation query date")
    season = season_for_month(as_of.month)
    rows = []
    catalog = set()
    evaluated_interactions = 0
    skipped_customers = 0
    for cid, group in future.groupby("customer_id"):
        if not cold and cid not in model.customers_df.index:
            skipped_customers += 1
            continue
        evaluated_interactions += len(group)
        relevant = set(group.service_id)
        ranked = model.rank_profile(profiles[cid], None if cold else cid, method, season)[:k]
        recs = [sid for sid, _ in ranked]
        catalog.update(recs)
        rows.append(ranking_metrics(recs, relevant, k))
    if not rows:
        raise ValueError("No eligible customers in evaluation window")
    result = {
        f"{name}@{k}": round(float(np.mean([r[name] for r in rows])), 6)
        for name in ("hit_rate", "precision", "recall", "ndcg")
    }
    result.update(
        customers=len(rows),
        heldout_interactions=evaluated_interactions,
        skipped_customers_without_history=skipped_customers,
        catalog_coverage=round(len(catalog) / len(model.services_dict), 6),
        recommended_services=len(catalog),
        catalog_size=len(model.services_dict),
        as_of=str(as_of.date()),
    )
    return result


def urgency_metrics(model, customers, future):
    merged = future.merge(customers, on="customer_id", validate="many_to_one")
    learned = model.urgency.predict_frame(merged)
    rule = [
        rule_urgency(
            r.service_id, r.season, r.building_age_years, r.days_since_last_service, r.region
        )
        for r in merged.itertuples()
    ]
    mean = np.full(len(merged), model.training_urgency_mean)
    result = {"test_interactions": len(merged)}
    for name, pred in (
        ("gradient_boosting", learned),
        ("rule_baseline", rule),
        ("training_mean", mean),
    ):
        error = np.asarray(pred) - merged.urgency_score.to_numpy()
        result[name] = {
            "mae": round(float(np.abs(error).mean()), 6),
            "rmse": round(float(np.sqrt((error**2).mean())), 6),
        }
    return result


def fit_model(customers, train, services, cb_weight=0.4, n_components=3):
    model = HybridRecommender(cb_weight, 1 - cb_weight, n_components).fit(
        customers, train, services
    )
    counts = train.groupby("service_id").size().reindex(services.service_id, fill_value=0)
    model.popularity = (counts / max(int(counts.max()), 1)).to_dict()
    model.training_urgency_mean = float(train.urgency_score.mean())
    return model


def run_evaluation(data_dir=ROOT / "data", k=5):
    customers, interactions, services = load_data(Path(data_dir))
    interactions = interactions[interactions.completed].copy()
    # Entire cold cohort is excluded before any transform/model/hyperparameter fit.
    ordered = sorted(
        customers.customer_id, key=lambda cid: hashlib.sha256(f"42:{cid}".encode()).hexdigest()
    )
    cold_ids = set(ordered[: max(1, len(ordered) // 5)])
    warm = interactions[~interactions.customer_id.isin(cold_ids)]
    train, validation, test = temporal_split(warm)
    candidates = []
    for components in (2, 3):
        model = fit_model(customers, train, services, n_components=components)
        for weight in (0.0, 0.4, 0.7, 1.0):
            model.cb_weight, model.cf_weight = weight, 1 - weight
            metrics = evaluate_ranking(model, train, validation, customers, k=k)
            candidates.append(dict(cb_weight=weight, svd_components=components, **metrics))
    # Tie policy is deterministic. Test data never selects hyperparameters.
    best = max(candidates, key=lambda row: row[f"ndcg@{k}"])
    combined = pd.concat([train, validation], ignore_index=True)
    final = fit_model(customers, combined, services, best["cb_weight"], best["svd_components"])
    cold_test = interactions[
        interactions.customer_id.isin(cold_ids) & (interactions.date >= test.date.min())
    ]
    warm_results = {
        method: evaluate_ranking(final, combined, test, customers, method, k)
        for method in (
            "hybrid",
            "default_40_60",
            "collaborative",
            "content",
            "popularity",
            "profile_rule",
        )
    }
    cold_results = {
        method: evaluate_ranking(
            final, combined, cold_test, customers, method, k, cold=True, query_date=test.date.min()
        )
        for method in ("content", "popularity", "profile_rule")
    }
    report = dict(
        schema_version=2,
        seed=42,
        synthetic_data=True,
        data_fingerprint=data_fingerprint(Path(data_dir)),
        protocol="Global date 60/20/20 split, cold customers excluded from every fit; frozen query per customer; repeat bookings allowed.",
        relevance="Any distinct completed booked service in the future window, regardless of rating; not expert relevance labels.",
        splits=dict(
            train=len(train),
            validation=len(validation),
            test=len(test),
            cold_customers_reserved=len(cold_ids),
            cold_test=len(cold_test),
            train_end=train.date.max(),
            validation_start=validation.date.min(),
            validation_end=validation.date.max(),
            test_start=test.date.min(),
        ),
        selected=dict(
            cb_weight=best["cb_weight"],
            cf_weight=1 - best["cb_weight"],
            svd_components=best["svd_components"],
        ),
        validation_candidates=candidates,
        warm=warm_results,
        cold=cold_results,
        urgency=urgency_metrics(final, customers, test),
        limitations=[
            "Synthetic data only; no evidence of real customer benefit.",
            "Profile and urgency rule baselines share simulator assumptions and have privileged knowledge.",
            "Only ten services; top-five hit rate is inherently generous.",
            "Unbooked services are unobserved, not confirmed irrelevant.",
            "No causal lift, calibrated confidence, or professional pest-risk validation.",
            "One fixed split and seed; uncertainty intervals and broader stability studies remain future work.",
        ],
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/evaluation.json")
    args = parser.parse_args()
    report = run_evaluation(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: report[key] for key in ("splits", "selected", "warm", "cold", "urgency")},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
