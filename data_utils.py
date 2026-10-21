"""CSV loading and quality checks shared by training and evaluation."""

import hashlib
from pathlib import Path

import pandas as pd

from domain import ROOT, build_profile, eligible, season_for_month


def load_data(data_dir: Path = ROOT / "data") -> tuple:
    customers = pd.read_csv(data_dir / "customers.csv", dtype={"zip_code": str})
    interactions = pd.read_csv(data_dir / "interactions.csv")
    services = pd.read_csv(data_dir / "services.csv")
    validate_data(customers, interactions, services)
    return customers, interactions, services


def data_fingerprint(data_dir: Path) -> str:
    digest = hashlib.sha256()
    for name in ("customers.csv", "interactions.csv", "services.csv"):
        digest.update((data_dir / name).read_bytes())
    digest.update((ROOT / "config/regions.json").read_bytes())
    return digest.hexdigest()


def validate_data(customers, interactions, services) -> None:
    for frame, key in (
        (customers, "customer_id"),
        (interactions, "interaction_id"),
        (services, "service_id"),
    ):
        if frame.empty or frame.isna().any().any() or not frame[key].is_unique:
            raise ValueError(f"Empty, missing or duplicate data in {key}")
    if not set(interactions.customer_id) <= set(customers.customer_id):
        raise ValueError("Unknown customer in interactions")
    if not set(interactions.service_id) <= set(services.service_id):
        raise ValueError("Unknown service in interactions")
    if (
        not interactions.rating.between(1, 5).all()
        or not interactions.urgency_score.between(1, 10).all()
    ):
        raise ValueError("Rating or urgency outside its valid range")
    if not interactions.days_since_last_service.between(0, 36500).all():
        raise ValueError("Invalid visit interval")
    profiles = {}
    for row in customers.to_dict("records"):
        profile = build_profile(
            row["property_type"], row["zip_code"], row["building_age_years"], row["region"]
        )
        if (
            row["is_commercial"] != profile["is_commercial"]
            or row["is_desert_adjacent"] != profile["is_desert_adjacent"]
        ):
            raise ValueError("Profile flags disagree with regional configuration")
        profiles[row["customer_id"]] = profile
    catalog = services.set_index("service_id").to_dict("index")
    members = customers.set_index("customer_id").member_since.to_dict()
    for cid, group in interactions.groupby("customer_id"):
        group = group.sort_values(["date", "interaction_id"])
        previous_date = pd.Timestamp(members[cid])
        seen = set()
        for row in group.to_dict("records"):
            date = pd.Timestamp(row["date"])
            if (
                date <= previous_date
                or row["days_since_last_service"] != (date - previous_date).days
            ):
                raise ValueError("Chronology or service interval inconsistent")
            if row["season"] != season_for_month(date.month):
                raise ValueError("Season disagrees with visit date")
            if bool(row["repeat_booking"]) != (row["service_id"] in seen):
                raise ValueError("Repeat flag disagrees with prior history")
            if not eligible(catalog[row["service_id"]], profiles[cid]):
                raise ValueError("Incompatible service in interactions")
            seen.add(row["service_id"])
            previous_date = date
