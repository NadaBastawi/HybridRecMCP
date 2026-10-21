"""API contract, validation, security and actual telemetry regressions."""

import pytest
from fastapi.testclient import TestClient

from main import create_app
from settings import Settings, scrub_sentry

NEW = dict(property_type="residential_house", zip_code="85743", building_age_years=30)


@pytest.mark.parametrize(
    "path,payload",
    [
        ("/recommend", {"customer_id": "C0001"}),
        ("/recommend/new-customer", NEW),
        ("/services", None),
        ("/monitoring", None),
    ],
)
@pytest.mark.parametrize("key", [None, "wrong-key"])
def test_auth_required(api_client, path, payload, key):
    headers = {} if key is None else {"X-API-Key": key}
    response = (
        api_client.get(path, headers=headers)
        if payload is None
        else api_client.post(path, json=payload, headers=headers)
    )
    assert response.status_code == 401


@pytest.mark.parametrize("key", ["", "short", "your-api-key-here"])
def test_missing_secret_fails_startup(monkeypatch, key):
    monkeypatch.setenv("API_KEY", key)
    with pytest.raises(ValueError, match="API_KEY"):
        with TestClient(create_app()):
            pass


def test_health(api_client):
    assert api_client.get("/health").json() == dict(
        status="ok", model_loaded=True, model_version="2.0.0", synthetic_data=True
    )


def test_success_contracts(api_client, auth):
    a = api_client.post("/recommend", json={"customer_id": "C0001"}, headers=auth)
    b = api_client.post("/recommend/new-customer", json=NEW, headers=auth)
    assert a.status_code == b.status_code == 200
    for response in [a, b]:
        data = response.json()
        assert data["synthetic_data"] and "unofficial" in data["disclaimer"]
        assert len(data["recommendations"]) == 5
        assert "score" in data["recommendations"][0]
        assert data["recommendations"][0]["requires_assessment"]
    catalog = api_client.get("/services", headers=auth)
    assert catalog.status_code == 200 and len(catalog.json()) == 10
    assert catalog.json()[0]["price_basis"] == "illustrative, not a quote"
    unknown = api_client.post("/recommend", json={"customer_id": "C9999"}, headers=auth)
    assert unknown.status_code == 404 and unknown.json() == {"detail": "Customer not found"}


@pytest.mark.parametrize(
    "field,value",
    [
        ("season", "monsoon"),
        ("season", None),
        ("top_n", 0),
        ("top_n", 11),
        ("top_n", None),
        ("top_n", True),
        ("days_since_last_service", -1),
        ("days_since_last_service", 36501),
        ("building_age_years", -1),
        ("building_age_years", 201),
        ("building_age_years", 1.2),
        ("property_type", "castle"),
        ("zip_code", "123"),
        ("zip_code", "abcde"),
        ("zip_code", 85743),
        ("region", "unknown"),
        ("unexpected", "ignored?"),
    ],
)
def test_invalid_new_inputs(api_client, auth, field, value):
    response = api_client.post("/recommend/new-customer", json={**NEW, field: value}, headers=auth)
    assert response.status_code == 422


@pytest.mark.parametrize("cid", ["UNKNOWN", "C1", "C0001/../../etc", ""])
def test_invalid_ids(api_client, auth, cid):
    assert api_client.post("/recommend", json={"customer_id": cid}, headers=auth).status_code == 422


def test_explicit_unknown_history_and_legacy_default(api_client, auth):
    unknown = api_client.post(
        "/recommend/new-customer", json={**NEW, "days_since_last_service": None}, headers=auth
    )
    assert unknown.status_code == 200
    assert all(
        r["urgency_score"] is None and r["urgency_label"] == "UNKNOWN"
        for r in unknown.json()["recommendations"]
    )
    legacy = api_client.post("/recommend/new-customer", json=NEW, headers=auth)
    assert all(r["urgency_score"] is not None for r in legacy.json()["recommendations"])
    assert api_client.app.state.prediction_logger.get_recent_logs()


def test_unseen_zip_and_ohio(api_client, auth):
    unknown = api_client.post(
        "/recommend/new-customer", json={**NEW, "zip_code": "99999"}, headers=auth
    ).json()
    assert unknown["profile"]["location_supported"] is False
    assert all("limited" in r["explanation"] for r in unknown["recommendations"])
    ohio = api_client.post(
        "/recommend/new-customer",
        json={**NEW, "region": "ohio", "zip_code": "43215", "top_n": 10},
        headers=auth,
    ).json()
    assert all(r["category"] not in ["commercial", "scorpion"] for r in ohio["recommendations"])


def test_real_private_telemetry(api_client, auth):
    assert (
        api_client.get("/monitoring", headers=auth).json()["overall_status"] == "INSUFFICIENT_DATA"
    )
    for _ in range(8):
        api_client.post("/recommend/new-customer", json=NEW, headers=auth)
    report = api_client.get("/monitoring", headers=auth).json()
    assert report["total_predictions"] == 40 and report["drift_analysis"]
    records = api_client.app.state.prediction_logger.get_recent_logs()
    assert records and "building_age_years" in records[0]
    assert not any(
        key in records[0] for key in ["zip_code", "customer_id", "API_KEY", "name", "email"]
    )


def test_sentry_scrubbing():
    event = {
        "user": {"email": "private"},
        "request": {"headers": {"X-API-Key": "secret"}},
        "breadcrumbs": [],
        "message": "redacted event",
    }
    assert scrub_sentry(event, {}) == {"message": "redacted event"}
    assert "local-test-only-secret" not in repr(Settings(api_key="local-test-only-secret"))
