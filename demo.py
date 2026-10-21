"""Standalone synthetic-data presentation for local and Community Cloud use."""

import html
import json
import logging
import os

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

# Community Cloud may supply legacy False, which still displays stack traces.
# Apply strict redaction before application imports can raise an exception.
st.set_option("client.showErrorDetails", "none")

from domain import DISCLAIMER, PROPERTY_TYPES, REGIONS, ROOT  # noqa: E402
from model_store import demo_cache_dir, prepare_demo_model  # noqa: E402
from train import artifact_metadata  # noqa: E402

st.set_page_config(
    page_title="Property Service Advisor | Independent Demo", page_icon="🌿", layout="wide"
)
st.markdown(
    """<style>
.block-container {max-width:1120px;padding-top:2.5rem;}
.stApp {background:#f5f7f5;color:#172d28;}
h1,h2,h3 {color:#153e35;}
[data-testid="stMetric"] {background:white;border:1px solid #dce5df;border-radius:12px;padding:18px;}
.service-card {background:white;border:1px solid #dce5df;border-radius:14px;padding:22px;margin:14px 0;}
.eyebrow {color:#527368;font-size:13px;font-weight:700;letter-spacing:2px;}
.pill {background:#e7f1eb;border-radius:18px;padding:5px 12px;color:#245d43;font-size:13px;}
[data-testid="stToolbar"] {visibility:hidden;}
</style>""",
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="eyebrow">HYBRIDRECMCP · INDEPENDENT PROOF OF CONCEPT</div>', unsafe_allow_html=True
)
st.title("A clearer next step for every property")
st.write("Explore relevant services and possible follow-ups using a simulated customer profile.")
st.info(
    "Synthetic data · Illustrative pricing · Staff review required · No company affiliation or endorsement"
)


@st.cache_resource(show_spinner=False)
def load_engine(fingerprint, cache_path):
    return prepare_demo_model(cache_path)


def default_region():
    value = os.getenv("DEMO_DEFAULT_REGION")
    if value is None:
        try:
            value = st.secrets.get("DEMO_DEFAULT_REGION", "tucson")
        except (FileNotFoundError, StreamlitSecretNotFoundError):
            value = "tucson"
    return value if value in REGIONS else "tucson"


try:
    with st.spinner("Preparing the synthetic demonstration. The first visit may take a moment…"):
        engine = load_engine(
            json.dumps(artifact_metadata(ROOT / "data"), sort_keys=True), str(demo_cache_dir())
        )
except Exception as exc:
    logging.getLogger(__name__).error("Demo preparation failed (%s)", type(exc).__name__)
    st.error(
        "The demonstration could not initialize. Please try again later or contact the project developer."
    )
    st.stop()

left, right = st.columns([1, 1.65], gap="large")
with left:
    st.subheader("1. Choose a customer scenario")
    scenario = st.radio(
        "Customer scenario",
        ["New customer", "Existing synthetic customer"],
        horizontal=True,
        key="scenario",
    )
    region = st.selectbox(
        "Demonstration region",
        list(REGIONS),
        index=list(REGIONS).index(default_region()),
        format_func=lambda r: REGIONS[r]["label"],
        key="demo_region",
    )
    # Widgets rerun individually so stale results can be removed as inputs change.
    with st.container(border=True):
        if scenario == "New customer":
            prop = st.selectbox(
                "Property type",
                list(PROPERTY_TYPES),
                format_func=lambda p: p.replace("_", " ").title(),
                key="property_type",
            )
            zip_code = st.text_input(
                "ZIP code",
                value="85743" if region == "tucson" else "43215",
                max_chars=5,
                key=f"zip_{region}",
            )
            age = st.number_input(
                "Building age (years)",
                min_value=0,
                max_value=200,
                value=30,
                step=1,
                key="building_age",
            )
        else:
            customers = engine.customers_df[engine.customers_df.region == region]
            if customers.empty:
                st.info(
                    "There are no synthetic customer records for this region in the prepared dataset."
                )
                st.stop()
            cid = st.selectbox(
                "Synthetic customer ID", customers.index.tolist(), key=f"customer_id_{region}"
            )
            profile = engine.customers_df.loc[cid]
            st.caption(
                f"{profile['property_type'].replace('_', ' ').title()} · {REGIONS[profile['region']]['label']} · {profile['building_age_years']} years"
            )
        season = st.selectbox(
            "Season", ["spring", "summer", "fall", "winter"], index=1, key="season"
        )
        if scenario == "New customer":
            history = st.radio(
                "Previous service timing", ["Unknown", "Known"], horizontal=True, key="history_mode"
            )
            days = (
                st.number_input(
                    "Days since last service",
                    min_value=0,
                    max_value=36500,
                    value=None,
                    step=1,
                    placeholder="Enter a known scenario interval",
                    key="new_days",
                )
                if history == "Known"
                else None
            )
            inputs = dict(
                scenario=scenario,
                region=region,
                property_type=prop,
                zip_code=zip_code,
                building_age_years=age,
                season=season,
                history=history,
                days_since_last_service=days,
            )
        else:
            days = st.number_input(
                "Days since last service",
                min_value=0,
                max_value=36500,
                value=400,
                step=1,
                key="existing_days",
            )
            inputs = dict(
                scenario=scenario,
                region=region,
                customer_id=cid,
                season=season,
                days_since_last_service=days,
            )
        fingerprint = json.dumps(inputs, sort_keys=True)
        if st.session_state.get("result", {}).get("fingerprint") != fingerprint:
            st.session_state.pop("result", None)
        submitted = st.button("Explore relevant services", type="primary", use_container_width=True)
    st.caption(
        "Use demonstration details only. Staff must confirm conditions; this screen does not diagnose an infestation or schedule treatment."
    )
with right:
    st.subheader("2. Review the next conversation")
    st.caption(
        "Services are ranked by estimated relevance. Priority labels are a separate simulated follow-up assessment."
    )
    if submitted:
        try:
            if scenario == "New customer":
                if history == "Known" and days is None:
                    raise ValueError("Known timing needs an interval")
                recs = engine.recommend_cold_start(
                    prop, zip_code, int(age), season, days, region=region
                )
                title = f"{prop.replace('_', ' ').title()} · {REGIONS[region]['label']}"
            else:
                recs = engine.recommend(cid, season=season, days_since_last=int(days))
                title = f"Synthetic customer {cid}"
            st.session_state["result"] = dict(
                recs=recs, title=title, inputs=dict(inputs), fingerprint=fingerprint
            )
        except ValueError:
            st.error(
                "Enter a five-digit ZIP code, valid property details, and a service interval if timing is known."
            )
            st.session_state.pop("result", None)
        except Exception as exc:
            logging.getLogger(__name__).error("Demo recommendation failed (%s)", type(exc).__name__)
            st.error("Recommendations are temporarily unavailable. Please try again later.")
            st.session_state.pop("result", None)
    result = st.session_state.get("result")
    if result:
        st.write(result["title"])
        saved = result["inputs"]
        timing = (
            "Unknown service history"
            if saved["days_since_last_service"] is None
            else f"{saved['days_since_last_service']} days since service"
        )
        st.caption(
            f"Submitted scenario: {saved['season'].title()} · {timing}. Changing inputs clears these results."
        )
        recs = result["recs"]
        a, b = st.columns(2)
        a.metric("Relevant service ideas", len(recs))
        b.metric(
            "Higher-priority follow-ups",
            "Unknown"
            if saved["days_since_last_service"] is None
            else sum(r["urgency_label"] == "HIGH" for r in recs),
        )
        if saved["days_since_last_service"] is None:
            st.caption(
                "Priority is unknown because the previous service interval was not provided."
            )
        for i, rec in enumerate(recs, 1):
            priority = (
                "Priority unknown"
                if rec["urgency_label"] == "UNKNOWN"
                else f"{rec['urgency_label'].title()} simulated priority"
            )
            st.markdown(
                f"""<div class="service-card"><span class="pill">{i:02d} · {html.escape(priority)}</span>
<h3>{html.escape(rec["service_name"])}</h3><p>{html.escape(rec["explanation"])}</p>
<p><strong>Staff question:</strong> {html.escape(rec["follow_up_question"])}</p>
<strong>${rec["price_usd"]:,.0f}</strong> <span>illustrative only · not a quote</span></div>""",
                unsafe_allow_html=True,
            )
        st.success(
            "Suggested staff action: confirm property conditions, ask about observed signs, and discuss whether an inspection is appropriate."
        )
    else:
        st.markdown(
            """<div class="service-card"><h3>From a property profile to a useful follow-up</h3>
<p>Start with a new homeowner, or choose a synthetic customer with service history.</p>
<p>Review relevant service ideas, then use the priority labels to decide which questions staff should ask next.</p></div>""",
            unsafe_allow_html=True,
        )

with st.expander("Technical context and limitations"):
    st.write(DISCLAIMER)
    st.write(
        "The engine supports blending property profiles with service-history patterns. New customers use profile similarity. Priority is separate, and is not estimated when timing is unknown. Rankings are not probabilities or calibrated confidence."
    )
    st.caption(
        f"Validation-selected relevance weights: profile {engine.cb_weight:.0%}, personal service history {engine.cf_weight:.0%}. These weights describe this synthetic task only."
    )
    st.write(
        "Card explanations describe documented profile/catalog rules and useful staff questions, not hidden-model feature attribution. Tucson and Ohio are independent demonstration scenarios; ZIP groupings and prices are assumptions."
    )
    evaluation = json.loads((ROOT / "reports/evaluation.json").read_text(encoding="utf-8"))
    st.json({key: evaluation[key] for key in ["selected", "warm", "cold", "urgency"]})

st.divider()
st.markdown(
    "**HybridRecMCP** · Developed by **Nada Bastawi** · [GitHub repository](https://github.com/NadaBastawi/HybridRecMCP)"
)
st.caption(DISCLAIMER)
