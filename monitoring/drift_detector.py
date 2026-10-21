"""Drift diagnostics on actual logged features; drift is not model accuracy."""

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

MIN_SAMPLES = 20


def calculate_psi(reference, production, bins=10):
    reference = pd.Series(reference).dropna()
    production = pd.Series(production).dropna()
    if reference.empty or production.empty:
        raise ValueError("Nonempty reference and production samples required")
    if pd.api.types.is_numeric_dtype(reference):
        reference = reference[np.isfinite(reference)]
        production = production[np.isfinite(production)]
        if reference.empty or production.empty:
            raise ValueError("Finite samples required")
        edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
        # Keep reference extremes as internal edges; overflow must not be discarded.
        edges = np.r_[
            -np.inf,
            np.nextafter(edges[0], -np.inf),
            edges[1:-1],
            np.nextafter(edges[-1], np.inf),
            np.inf,
        ]
        edges = np.unique(edges)
        ref = np.histogram(reference, bins=edges)[0].astype(float)
        prod = np.histogram(production, bins=edges)[0].astype(float)
    else:
        categories = sorted(set(map(str, reference)) | set(map(str, production)))
        ref = (
            reference.astype(str)
            .value_counts()
            .reindex(categories, fill_value=0)
            .to_numpy(dtype=float)
        )
        prod = (
            production.astype(str)
            .value_counts()
            .reindex(categories, fill_value=0)
            .to_numpy(dtype=float)
        )
    ref = (ref + 1e-4) / (ref.sum() + 1e-4 * len(ref))
    prod = (prod + 1e-4) / (prod.sum() + 1e-4 * len(prod))
    return float(np.sum((prod - ref) * np.log(prod / ref)))


def detect_feature_drift(reference_df, production_df):
    report = {}
    for feature in (
        "building_age_years",
        "urgency_score",
        "score",
        "property_type",
        "season",
        "region",
    ):
        if feature not in reference_df or feature not in production_df:
            continue
        ref, prod = reference_df[feature].dropna(), production_df[feature].dropna()
        if min(len(ref), len(prod)) < MIN_SAMPLES:
            continue
        psi = calculate_psi(ref, prod)
        details = dict(
            psi_score=round(psi, 6),
            reference_samples=len(ref),
            production_samples=len(prod),
            status="ALERT" if psi > 0.25 else "WARNING" if psi > 0.1 else "OK",
        )
        if pd.api.types.is_numeric_dtype(ref):
            stat, p_value = ks_2samp(ref, prod)
            details.update(ks_statistic=float(stat), p_value=float(p_value))
        report[feature] = details
    return report


def get_drift_report(logs=None):
    logs = logs or []
    if len(logs) < 2 * MIN_SAMPLES:
        return dict(
            overall_status="INSUFFICIENT_DATA",
            total_predictions=len(logs),
            drift_analysis={},
            note="At least 40 logged recommendations required; rows from one request are correlated.",
        )
    data = pd.DataFrame(logs)
    cut = len(data) // 2
    analysis = detect_feature_drift(data.iloc[:cut], data.iloc[cut:])
    statuses = [row["status"] for row in analysis.values()]
    overall = (
        ("ALERT" if "ALERT" in statuses else "WARNING" if "WARNING" in statuses else "OK")
        if analysis
        else "INSUFFICIENT_DATA"
    )
    return dict(
        overall_status=overall,
        total_predictions=len(logs),
        drift_analysis=analysis,
        note="First half of retained recent predictions versus second half; descriptive telemetry, not performance validation.",
    )


class DriftDetector:
    _calculate_psi = staticmethod(calculate_psi)
    detect_feature_drift = staticmethod(detect_feature_drift)
    get_drift_report = staticmethod(get_drift_report)
