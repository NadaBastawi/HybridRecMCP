"""Check staff prompts against actual scenario rules, without claiming model attribution."""

import pytest

from domain import build_profile
from explanations import explain_service


@pytest.mark.parametrize(
    "service,category,property_type,age,phrase",
    [
        ("S02", "termite", "residential_house", 45, "older-building"),
        ("S02", "termite", "residential_house", 10, "without assuming"),
        ("S03", "termite", "residential_house", 45, "requires inspection evidence"),
        ("S04", "bed_bug", "residential_apartment", 30, "apartment profiles"),
        ("S05", "rodent", "commercial_warehouse", 30, "rodent-service weight"),
        ("S07", "ant_roach", "commercial_warehouse", 30, "service emphasis"),
    ],
)
def test_service_context_matches_profile_rules(service, category, property_type, age, phrase):
    profile = build_profile(property_type, "85743", age)
    text, question = explain_service(service, category, profile, "summer", None)
    assert phrase in text and "timing is unknown" in text and question.endswith("?")


def test_unknown_history_does_not_invoke_priority_or_change_ranking(engine, monkeypatch):
    known = engine.recommend_cold_start("residential_house", "85743", 30, days_since_last=400)

    def forbidden(frame):
        raise AssertionError("Unknown timing cannot be scored as a made-up interval")

    monkeypatch.setattr(engine.urgency, "predict_frame", forbidden)
    unknown = engine.recommend_cold_start("residential_house", "85743", 30, days_since_last=None)
    assert [(r["service_id"], r["score"]) for r in known] == [
        (r["service_id"], r["score"]) for r in unknown
    ]
    assert all(r["urgency_score"] is None for r in unknown)
