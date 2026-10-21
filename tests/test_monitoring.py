"""PSI numerical edge cases, real features, privacy and insufficient-data status."""

import math

import pytest

from monitoring.drift_detector import calculate_psi, get_drift_report
from monitoring.logger import PredictionLogger


@pytest.mark.parametrize(
    "reference,production",
    [([5] * 30, [5] * 30), ([0] * 30, [1000] * 30), (["a"] * 30, ["b"] * 30)],
)
def test_psi_edges(reference, production):
    value = calculate_psi(reference, production)
    assert math.isfinite(value) and value >= 0
    assert (value == 0) == (reference == production)


def test_empty_and_missing_features():
    with pytest.raises(ValueError):
        calculate_psi([], ["a"])
    assert get_drift_report([{"timestamp": "now"}] * 50)["overall_status"] == "INSUFFICIENT_DATA"


def test_shift_detected():
    logs = [{"building_age_years": 10, "property_type": "residential_house"}] * 30
    logs += [{"building_age_years": 100, "property_type": "commercial_office"}] * 30
    report = get_drift_report(logs)
    assert report["overall_status"] == "ALERT"
    assert report["drift_analysis"]["building_age_years"]["psi_score"] > 0.25


def test_private_log(tmp_path):
    log = PredictionLogger(tmp_path)
    try:
        log.log_prediction(
            "C0001",
            "S01",
            0.5,
            7.4,
            {
                "zip_code": "85743",
                "API_KEY": "secret",
                "building_age_years": 20,
                "region": "tucson",
            },
        )
        row = log.get_recent_logs()[0]
        assert row["urgency_score"] == 7.4 and row["building_age_years"] == 20
        assert "C0001" not in log.path.read_text() and "secret" not in log.path.read_text()
    finally:
        log.close()
