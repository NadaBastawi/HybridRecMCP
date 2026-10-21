"""Hybrid relevance ranking with separate synthetic urgency estimates."""

import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder

from domain import DISCLAIMER, build_profile, eligible
from explanations import explain_service
from schemas import NewCustomerRequest, RecommendRequest

CB_WEIGHT_DEFAULT = 0.4
CF_WEIGHT_DEFAULT = 0.6
SVD_COMPONENTS_DEFAULT = 3
RANDOM_SEED = 42
MODEL_VERSION = "2.0.0"


def profile_transformer():
    return ColumnTransformer(
        [
            (
                "category",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                ["property_type", "region"],
            ),
            ("age", MinMaxScaler(clip=True), ["building_age_years"]),
            ("flags", "passthrough", ["is_desert_adjacent", "is_commercial"]),
        ],
        sparse_threshold=0,
    )


class ContentBasedRecommender:
    """Cosine similarity to service centroids from training customers only."""

    def __init__(self):
        self.transformer = profile_transformer()

    def fit(self, customers_df, interactions_df, services_df):
        self.customers = customers_df.set_index("customer_id", drop=False)
        features = self.transformer.fit_transform(customers_df)
        self.customer_vectors = dict(zip(customers_df.customer_id, features, strict=True))
        high = interactions_df[interactions_df.rating >= 4]
        self.service_affinity = {}
        for sid in services_df.service_id:
            ids = high.loc[high.service_id == sid, "customer_id"]
            vectors = [self.customer_vectors[cid] for cid in ids]
            self.service_affinity[sid] = (
                np.mean(vectors, axis=0) if vectors else np.zeros(features.shape[1])
            )
        return self

    def score_profile(self, profile):
        vec = self.transformer.transform(pd.DataFrame([profile]))
        return {
            sid: float(np.clip(cosine_similarity(vec, [affinity])[0, 0], 0, 1))
            for sid, affinity in self.service_affinity.items()
        }

    def recommend(self, customer_id, top_n=5):
        if customer_id not in self.customers.index:
            return []
        scores = self.score_profile(self.customers.loc[customer_id].to_dict())
        return sorted(scores.items(), key=lambda p: (-p[1], p[0]))[:top_n]


class CollaborativeFilteringRecommender:
    """Iterative SVD completion: missing ratings are unknown, never explicit dislikes.

    Observed repeated ratings are averaged. Missing entries start at smoothed item
    means, then are updated by low-rank reconstruction while observed cells stay fixed.
    This is a demonstration matrix-completion method, not implicit-feedback ALS.
    """

    def __init__(self, n_components=SVD_COMPONENTS_DEFAULT):
        if n_components < 1:
            raise ValueError("SVD components must be positive")
        self.n_components = n_components

    def fit(self, interactions_df, service_ids=None):
        table = interactions_df.pivot_table(
            index="customer_id", columns="service_id", values="rating", aggfunc="mean"
        )
        self.service_ids = sorted(service_ids if service_ids is not None else table.columns)
        table = table.reindex(columns=self.service_ids)
        self.customer_index = {cid: i for i, cid in enumerate(table.index)}
        values = table.to_numpy(dtype=float)
        observed = np.isfinite(values)
        overall = float(interactions_df.rating.mean())
        sums = np.nansum(values, axis=0)
        counts = observed.sum(axis=0)
        prior = (sums + 5 * overall) / (counts + 5)
        filled = np.where(observed, values, prior)
        self.effective_components = min(self.n_components, max(1, min(filled.shape) - 1))
        if min(filled.shape) < 2:
            self.reconstructed = filled
            return self
        for _ in range(12):
            means = filled.mean(axis=1, keepdims=True)
            self.svd = TruncatedSVD(
                n_components=self.effective_components, random_state=RANDOM_SEED
            )
            factors = self.svd.fit_transform(filled - means)
            reconstructed = np.clip(factors @ self.svd.components_ + means, 1, 5)
            filled = np.where(observed, values, reconstructed)
        self.reconstructed = reconstructed
        return self

    def scores(self, customer_id):
        if customer_id not in self.customer_index:
            return {}
        row = self.reconstructed[self.customer_index[customer_id]] / 5
        return dict(zip(self.service_ids, map(float, row), strict=True))

    def recommend(self, customer_id, top_n=5):
        return sorted(self.scores(customer_id).items(), key=lambda p: (-p[1], p[0]))[:top_n]


class UrgencyScorer:
    """Learn a noisy, hand-authored priority rule; no validated real-world risk claim."""

    def __init__(self):
        self.transformer = ColumnTransformer(
            [
                (
                    "category",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    ["season", "property_type", "service_id", "region"],
                ),
                ("numeric", "passthrough", ["building_age_years", "days_since_last_service"]),
            ],
            sparse_threshold=0,
        )
        self.model = GradientBoostingRegressor(
            n_estimators=100, max_depth=3, random_state=RANDOM_SEED
        )

    def fit(self, interactions_df, customers_df):
        merged = interactions_df.merge(customers_df, on="customer_id", validate="many_to_one")
        x = self.transformer.fit_transform(merged)
        self.model.fit(x, merged.urgency_score)
        return self

    def predict_frame(self, frame):
        return np.clip(self.model.predict(self.transformer.transform(frame)), 1, 10)

    def predict_urgency(self, customer_profile, service_id, season, days_since):
        frame = pd.DataFrame(
            [
                {
                    **customer_profile,
                    "service_id": service_id,
                    "season": season,
                    "days_since_last_service": days_since,
                }
            ]
        )
        return round(float(self.predict_frame(frame)[0]), 1)


class HybridRecommender:
    """Relevance and priority stay separate; recurring services may be recommended again."""

    def __init__(
        self,
        cb_weight=CB_WEIGHT_DEFAULT,
        cf_weight=CF_WEIGHT_DEFAULT,
        n_components=SVD_COMPONENTS_DEFAULT,
    ):
        if cb_weight < 0 or cf_weight < 0 or not np.isclose(cb_weight + cf_weight, 1):
            raise ValueError("Nonnegative hybrid weights must sum to one")
        self.cb_weight, self.cf_weight = cb_weight, cf_weight
        self.cb = ContentBasedRecommender()
        self.cf = CollaborativeFilteringRecommender(n_components)
        self.urgency = UrgencyScorer()
        self.services_dict = {}

    def fit(self, customers_df, interactions_df, services_df):
        completed = (
            interactions_df[interactions_df.completed].copy()
            if "completed" in interactions_df
            else interactions_df.copy()
        )
        if completed.empty:
            raise ValueError("Completed training interactions required")
        # Profiles belonging only to held-out users must not fit any transformation.
        training_customers = customers_df[
            customers_df.customer_id.isin(completed.customer_id)
        ].copy()
        self.customers_df = training_customers.set_index("customer_id")
        self.training_regions = set(training_customers.region)
        self.training_interaction_ids = set(completed.interaction_id)
        self.cb.fit(training_customers, completed, services_df)
        self.cf.fit(completed, services_df.service_id.tolist())
        self.urgency.fit(completed, training_customers)
        self.services_dict = services_df.set_index("service_id").to_dict("index")
        return self

    def rank_profile(self, profile, customer_id=None, method="hybrid", season="summer"):
        from domain import profile_prior

        cb = self.cb.score_profile(profile)
        cf = self.cf.scores(customer_id)
        if method == "popularity":
            scores = self.popularity
        elif method == "profile_rule":
            scores = {sid: profile_prior(profile, sid, season) for sid in self.services_dict}
        elif method == "content" or not cf:
            scores = cb
        elif method == "collaborative":
            scores = {sid: cf.get(sid, cb[sid]) for sid in self.services_dict}
        elif method == "default_40_60":
            scores = {sid: 0.4 * cb[sid] + 0.6 * cf.get(sid, cb[sid]) for sid in self.services_dict}
        else:
            scores = {
                sid: self.cb_weight * cb[sid] + self.cf_weight * cf.get(sid, cb[sid])
                for sid in self.services_dict
            }
        allowed = [
            (sid, float(value))
            for sid, value in scores.items()
            if eligible(self.services_dict[sid], profile)
        ]
        return sorted(allowed, key=lambda p: (-p[1], p[0]))

    def recommend(self, customer_id, top_n=5, season="summer", days_since_last=180):
        RecommendRequest(
            customer_id=customer_id,
            top_n=top_n,
            season=season,
            days_since_last_service=days_since_last,
        )
        if customer_id not in self.customers_df.index:
            raise KeyError("Unknown customer")
        profile = self.customers_df.loc[customer_id].to_dict()
        ranked = self.rank_profile(profile, customer_id, season=season)[:top_n]
        return self._build_recommendations(ranked, profile, season, days_since_last)

    def recommend_cold_start(
        self,
        property_type,
        zip_code,
        building_age_years,
        season="summer",
        days_since_last=180,
        top_n=5,
        region="tucson",
    ):
        NewCustomerRequest(
            property_type=property_type,
            zip_code=zip_code,
            building_age_years=building_age_years,
            season=season,
            days_since_last_service=days_since_last,
            top_n=top_n,
            region=region,
        )
        profile = build_profile(property_type, zip_code, building_age_years, region)
        ranked = self.rank_profile(profile, season=season)[:top_n]
        return self._build_recommendations(ranked, profile, season, days_since_last)

    def _build_customer_profile(self, property_type, zip_code, building_age_years, region="tucson"):
        return build_profile(property_type, zip_code, building_age_years, region)

    def _build_recommendations(self, ranked, profile, season, days):
        # Batch urgency inference is substantially cheaper than a DataFrame per service.
        frame = pd.DataFrame(
            [
                {**profile, "service_id": sid, "season": season, "days_since_last_service": days}
                for sid, _ in ranked
            ]
        )
        urgencies = (
            (self.urgency.predict_frame(frame) if days is not None else [None] * len(frame))
            if len(frame)
            else []
        )
        results = []
        for (sid, score), urgency in zip(ranked, urgencies, strict=True):
            info = self.services_dict[sid]
            explanation, question = explain_service(sid, info["category"], profile, season, days)
            if profile["region"] not in self.training_regions:
                explanation += (
                    " This region has no training examples; results are an extrapolation."
                )
            results.append(
                dict(
                    service_id=sid,
                    service_name=info["service_name"],
                    category=info["category"],
                    price_usd=info["price_usd"],
                    price_basis="illustrative, not a quote",
                    score=round(float(np.clip(score, 0, 1)), 4),
                    urgency_score=round(float(urgency), 1) if urgency is not None else None,
                    urgency_label=("HIGH" if urgency >= 7 else "MEDIUM" if urgency >= 4 else "LOW")
                    if urgency is not None
                    else "UNKNOWN",
                    explanation=explanation,
                    follow_up_question=question,
                    requires_assessment=True,
                )
            )
        return results

    def save(self, path="models/torco_recommender.pkl", metadata=None):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        joblib.dump(
            dict(version=MODEL_VERSION, model=self, metadata=metadata or {}, disclaimer=DISCLAIMER),
            temp,
        )
        os.replace(temp, path)

    @staticmethod
    def load(path="models/torco_recommender.pkl", expected_metadata=None):
        # Only load artifacts generated locally/by a trusted build: pickle is executable.
        envelope = joblib.load(path)
        if not isinstance(envelope, dict) or envelope.get("version") != MODEL_VERSION:
            raise ValueError("Incompatible model artifact; retrain with train.py")
        if expected_metadata is not None and envelope.get("metadata") != expected_metadata:
            raise ValueError("Stale model artifact; retrain with train.py")
        return envelope["model"]


if __name__ == "__main__":
    from train import main

    main()
