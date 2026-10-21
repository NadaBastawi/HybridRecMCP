"""Model regressions, eligibility, cold start and reproducibility."""

import numpy as np
import pytest
from pydantic import ValidationError

from domain import build_profile
from recommender import HybridRecommender


@pytest.mark.parametrize("top_n", [1, 3, 5, 10])
def test_existing_rankings(engine, top_n):
    a = engine.recommend("C0001", top_n=top_n)
    assert 0 < len(a) <= top_n
    assert len({r["service_id"] for r in a}) == len(a)
    assert [r["score"] for r in a] == sorted([r["score"] for r in a], reverse=True)
    assert all(0 <= r["score"] <= 1 and 1 <= r["urgency_score"] <= 10 for r in a)
    assert a == engine.recommend("C0001", top_n=top_n)


@pytest.mark.parametrize(
    "region,zip_code", [("tucson", "85743"), ("ohio", "43215"), ("tucson", "99999")]
)
@pytest.mark.parametrize("season", ["winter", "spring", "summer", "fall"])
def test_cold_profiles(engine, region, zip_code, season):
    recs = engine.recommend_cold_start(
        "residential_house", zip_code, 30, season=season, top_n=10, region=region
    )
    assert recs and all(r["category"] != "commercial" for r in recs)
    if region == "ohio":
        assert all(r["category"] != "scorpion" for r in recs)


def test_relevance_is_separate_from_urgency(engine):
    a = engine.recommend_cold_start(
        "residential_house", "85743", 45, season="winter", days_since_last=30
    )
    b = engine.recommend_cold_start(
        "residential_house", "85743", 45, season="summer", days_since_last=900
    )
    assert [(r["service_id"], r["score"]) for r in a] == [(r["service_id"], r["score"]) for r in b]
    assert any(x["urgency_score"] != y["urgency_score"] for x, y in zip(a, b, strict=True))


def test_profile_processing(engine):
    cols = engine.cb.transformer.named_transformers_["category"].get_feature_names_out()
    assert any("property_type_residential_house" in col for col in cols)
    vector = engine.cb.score_profile(
        {
            **build_profile("residential_house", "85743", 30),
            "property_type": "unseen_internal_category",
        }
    )
    assert all(np.isfinite(list(vector.values())))
    with pytest.raises(ValidationError):
        engine.recommend_cold_start("castle", "85743", 30)
    with pytest.raises(KeyError):
        engine.recommend("C9999")


def test_single_user_small_svd(dataset):
    customers, interactions, services = dataset
    one = customers.iloc[:1]
    model = HybridRecommender().fit(
        one, interactions[interactions.customer_id.isin(one.customer_id)], services
    )
    assert model.cf.effective_components == 1
    assert model.recommend("C0001")


def test_repeat_services_explicitly_allowed(engine, dataset):
    cid = "C0001"
    purchased = set(dataset[1].loc[dataset[1].customer_id == cid, "service_id"])
    assert purchased
    # All eligible services remain candidates even when the customer has history.
    recommendations = engine.recommend(cid, top_n=10)
    ids = {r["service_id"] for r in recommendations}
    assert purchased <= ids
    assert len(ids) == (10 if engine.customers_df.loc[cid, "is_commercial"] else 9)


def test_training_excludes_unknown_users(dataset):
    c, i, s = dataset
    train = i[~i.customer_id.isin(c.customer_id.tail(5))]
    model = HybridRecommender().fit(c, train, s)
    assert not set(c.customer_id.tail(5)) & set(model.customers_df.index)
    assert model.training_interaction_ids == set(train.interaction_id)


def test_model_roundtrip(engine, tmp_path):
    path = tmp_path / "model.pkl"
    engine.save(path, {"test": "fingerprint"})
    loaded = HybridRecommender.load(path, {"test": "fingerprint"})
    assert loaded.recommend("C0001") == engine.recommend("C0001")
    with pytest.raises(ValueError, match="Stale"):
        HybridRecommender.load(path, {"test": "different"})


def test_training_reproducible(dataset, engine):
    from evaluate import fit_model

    second = fit_model(*dataset)
    assert second.recommend("C0001") == engine.recommend("C0001")
