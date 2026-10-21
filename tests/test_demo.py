"""Presentation regression tests. A separate clean-copy readiness probe uses real training."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import model_store


@pytest.fixture
def app(engine, monkeypatch, tmp_path):
    monkeypatch.setenv("DEMO_MODEL_CACHE_DIR", str(tmp_path / "private-model"))
    monkeypatch.setenv("API_KEY", "private-value-must-never-appear")
    monkeypatch.setattr(model_store, "train_from_data", lambda: engine)
    value = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "demo.py"), default_timeout=60
    ).run()
    assert not value.exception and not value.error
    return value


def submit(app):
    app.button[0].click().run()
    assert not app.exception and not app.error
    assert app.metric[0].value == "5"
    return app.session_state["result"]


def test_demo_new_unknown_history_and_footer(app):
    result = submit(app)
    assert app.metric[1].value == "Unknown"
    assert result["inputs"]["days_since_last_service"] is None
    assert all(
        r["urgency_score"] is None and r["urgency_label"] == "UNKNOWN" for r in result["recs"]
    )
    markdown = " ".join(m.value for m in app.markdown)
    assert (
        "Developed by **Nada Bastawi**" in markdown
        and "https://github.com/NadaBastawi/HybridRecMCP" in markdown
    )
    assert "private-value-must-never-appear" not in markdown
    assert all(r["follow_up_question"].endswith("?") for r in result["recs"])
    assert len({r["explanation"] for r in result["recs"]}) == 5


def test_demo_known_history_and_existing(app):
    app.radio(key="history_mode").set_value("Known").run()
    app.button[0].click().run()
    assert app.error and not app.exception
    app.number_input(key="new_days").set_value(400).run()
    result = submit(app)
    assert all(r["urgency_score"] is not None for r in result["recs"])
    app.radio(key="scenario").set_value("Existing synthetic customer").run()
    result = submit(app)
    assert result["inputs"]["customer_id"] == "C0001"


@pytest.mark.parametrize(
    "change",
    ["region", "scenario", "property", "zip", "age", "season", "history", "days", "customer"],
)
def test_input_changes_clear_stale_results(app, change):
    if change == "days":
        app.radio(key="history_mode").set_value("Known").run()
        app.number_input(key="new_days").set_value(400).run()
    if change == "customer":
        app.radio(key="scenario").set_value("Existing synthetic customer").run()
    submit(app)
    if change == "region":
        app.selectbox(key="demo_region").set_value("ohio").run()
    elif change == "scenario":
        app.radio(key="scenario").set_value("Existing synthetic customer").run()
    elif change == "property":
        app.selectbox(key="property_type").set_value("residential_apartment").run()
    elif change == "zip":
        app.text_input(key="zip_tucson").set_value("85701").run()
    elif change == "age":
        app.number_input(key="building_age").set_value(45).run()
    elif change == "season":
        app.selectbox(key="season").set_value("winter").run()
    elif change == "history":
        app.radio(key="history_mode").set_value("Known").run()
    elif change == "days":
        app.number_input(key="new_days").set_value(401).run()
    else:
        app.selectbox(key="customer_id_tucson").select_index(1).run()
    assert not app.exception and not app.metric


def test_regions_and_invalid_zip(app):
    for region in ["ohio", "tucson"]:
        app.selectbox(key="demo_region").set_value(region).run()
        result = submit(app)
        assert result["inputs"]["region"] == region
        if region == "ohio":
            assert all(r["category"] != "scorpion" for r in result["recs"])
    app.text_input(key="zip_tucson").set_value("oops").run()
    app.button[0].click().run()
    assert not app.exception and app.error and not app.metric


def test_default_ohio(engine, monkeypatch, tmp_path):
    monkeypatch.setenv("DEMO_DEFAULT_REGION", "ohio")
    monkeypatch.setenv("DEMO_MODEL_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(model_store, "train_from_data", lambda: engine)
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "demo.py"), default_timeout=60
    ).run()
    assert app.selectbox(key="demo_region").value == "ohio" and not app.exception


def test_preparation_error_is_public_safe(monkeypatch, tmp_path):
    monkeypatch.setenv("DEMO_MODEL_CACHE_DIR", str(tmp_path))

    def fail(*args, **kwargs):
        raise RuntimeError("secret C:/internal/private/path")

    monkeypatch.setattr(model_store, "prepare_demo_model", fail)
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "demo.py"), default_timeout=60
    ).run()
    assert not app.exception and app.error
    assert "secret" not in app.error[0].value and "internal/private" not in app.error[0].value


def test_uncaught_errors_hide_types_messages_and_paths(app):
    broken = AppTest.from_string("raise RuntimeError('secret C:/internal/private/path')").run()
    assert len(broken.exception) == 1
    error = broken.exception[0].proto
    assert not error.type and not error.stack_trace and "secret" not in error.message
