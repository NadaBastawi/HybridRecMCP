"""FastAPI service for the independent synthetic-data proof of concept."""

import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request

from domain import DISCLAIMER, build_profile
from monitoring.drift_detector import get_drift_report
from monitoring.logger import PredictionLogger
from recommender import MODEL_VERSION, HybridRecommender
from schemas import HealthResponse, NewCustomerRequest, RecommendRequest, RecommendResponse, Service
from settings import Settings, scrub_sentry
from train import artifact_metadata

logger = logging.getLogger(__name__)


def create_app(settings=None, model=None):
    @asynccontextmanager
    async def lifespan(app):
        config = settings or Settings.from_env()
        if config.sentry_dsn:
            import sentry_sdk

            sentry_sdk.init(
                dsn=config.sentry_dsn,
                send_default_pii=False,
                traces_sample_rate=0.0,
                include_local_variables=False,
                before_send=scrub_sentry,
            )
        app.state.settings = config
        app.state.model = (
            model
            if model is not None
            else HybridRecommender.load(
                config.model_dir / "torco_recommender.pkl", artifact_metadata(config.data_dir)
            )
        )
        app.state.prediction_logger = PredictionLogger(config.log_dir)
        try:
            yield
        finally:
            app.state.prediction_logger.close()

    app = FastAPI(
        title="HybridRecMCP - Independent Demonstration",
        version=MODEL_VERSION,
        description=DISCLAIMER,
        lifespan=lifespan,
    )

    def require_api_key(
        request: Request, x_api_key: str | None = Header(default=None, alias="X-API-Key")
    ):
        if x_api_key is None or not hmac.compare_digest(
            x_api_key.encode(), request.app.state.settings.api_key.encode()
        ):
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

    def record(request, recs, profile, season, days):
        context = {**profile, "season": season, "days_since_last_service": days}
        try:
            for rec in recs:
                request.app.state.prediction_logger.log_prediction(
                    None, rec["service_id"], rec["score"], rec["urgency_score"], context
                )
        except OSError:
            logger.warning("Prediction telemetry write failed")

    @app.get("/")
    def root():
        return dict(
            service="HybridRecMCP",
            disclaimer=DISCLAIMER,
            endpoints=[
                "/recommend",
                "/recommend/new-customer",
                "/services",
                "/health",
                "/monitoring",
            ],
        )

    @app.get("/health", response_model=HealthResponse)
    def health(request: Request):
        ready = getattr(request.app.state, "model", None) is not None
        if not ready:
            raise HTTPException(503, "Model unavailable")
        return dict(status="ok", model_loaded=ready, model_version=MODEL_VERSION)

    @app.get("/services", response_model=list[Service], dependencies=[Depends(require_api_key)])
    def services(request: Request):
        return [
            dict(service_id=sid, **info)
            for sid, info in request.app.state.model.services_dict.items()
        ]

    @app.get("/monitoring", dependencies=[Depends(require_api_key)])
    def monitoring(request: Request):
        return get_drift_report(request.app.state.prediction_logger.get_recent_logs())

    @app.post(
        "/recommend", response_model=RecommendResponse, dependencies=[Depends(require_api_key)]
    )
    def recommend(payload: RecommendRequest, request: Request):
        engine = request.app.state.model
        if payload.customer_id not in engine.customers_df.index:
            raise HTTPException(404, "Customer not found")
        profile = engine.customers_df.loc[payload.customer_id].to_dict()
        recs = engine.recommend(
            payload.customer_id, payload.top_n, payload.season, payload.days_since_last_service
        )
        record(request, recs, profile, payload.season, payload.days_since_last_service)
        safe_profile = build_profile(
            profile["property_type"],
            str(profile["zip_code"]),
            int(profile["building_age_years"]),
            profile["region"],
        )
        return RecommendResponse(
            customer_id=payload.customer_id,
            customer_type="existing",
            profile=safe_profile,
            recommendations=recs,
        )

    @app.post(
        "/recommend/new-customer",
        response_model=RecommendResponse,
        dependencies=[Depends(require_api_key)],
    )
    def recommend_new(payload: NewCustomerRequest, request: Request):
        profile = build_profile(
            payload.property_type, payload.zip_code, payload.building_age_years, payload.region
        )
        recs = request.app.state.model.recommend_cold_start(
            payload.property_type,
            payload.zip_code,
            payload.building_age_years,
            payload.season,
            payload.days_since_last_service,
            payload.top_n,
            payload.region,
        )
        record(request, recs, profile, payload.season, payload.days_since_last_service)
        return RecommendResponse(customer_type="new", profile=profile, recommendations=recs)

    return app


app = create_app()
