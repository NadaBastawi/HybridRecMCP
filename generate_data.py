"""Reproducible synthetic bookings; every rule and price is illustrative."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from domain import (
    PROPERTY_TYPES,
    REGIONS,
    build_profile,
    eligible,
    profile_prior,
    rule_urgency,
    season_for_month,
)

SEED = 42
WINDOW_START = pd.Timestamp("2023-01-01")
WINDOW_END = pd.Timestamp("2025-12-31")
SERVICES = {
    "S01": ("General Pest Control", 120, "general"),
    "S02": ("Termite Inspection", 150, "termite"),
    "S03": ("Termite Treatment Consultation", 800, "termite"),
    "S04": ("Bed Bug Assessment", 400, "bed_bug"),
    "S05": ("Rodent Control Consultation", 200, "rodent"),
    "S06": ("Scorpion Control Consultation", 180, "scorpion"),
    "S07": ("Ant & Cockroach Consultation", 130, "ant_roach"),
    "S08": ("Commercial Pest Management", 500, "commercial"),
    "S09": ("Preventive Maintenance Plan", 300, "preventive"),
    "S10": ("Priority Inspection Request", 250, "emergency"),
}


def generate_services_df():
    return pd.DataFrame(
        [
            dict(
                service_id=sid,
                service_name=name,
                price_usd=price,
                category=category,
                suitable_residential=category != "commercial",
                suitable_commercial=True,
                peak_season="illustrative seasonal"
                if category in ("termite", "scorpion")
                else "year-round",
            )
            for sid, (name, price, category) in SERVICES.items()
        ]
    )


def generate_customers(n=500, region="tucson", seed=SEED):
    if n < 1 or region not in (*REGIONS, "both"):
        raise ValueError("Positive customer count and supported region required")
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        selected = ("ohio" if i % 4 == 3 else "tucson") if region == "both" else region
        prop = str(rng.choice(PROPERTY_TYPES, p=[0.4, 0.2, 0.12, 0.12, 0.08, 0.08]))
        profile = build_profile(
            prop,
            str(rng.choice(REGIONS[selected]["example_zips"])),
            int(rng.integers(1, 81)),
            selected,
        )
        rows.append(
            dict(
                customer_id=f"C{i + 1:04d}",
                **profile,
                member_since=(WINDOW_START - pd.Timedelta(days=int(rng.integers(1, 730))))
                .date()
                .isoformat(),
                num_units=int(rng.integers(1, 51)) if prop == "residential_apartment" else 1,
            )
        )
    return pd.DataFrame(rows)


def get_service_probabilities(
    property_type, zip_code, season, building_age, prev_services, region="tucson"
):
    profile = build_profile(property_type, str(zip_code), building_age, region)
    catalog = generate_services_df().set_index("service_id").to_dict("index")
    probabilities = {}
    for sid, info in catalog.items():
        weight = profile_prior(profile, sid, season) if eligible(info, profile) else 0.0
        if sid == "S09" and len(prev_services) >= 3:
            weight += 0.12
        probabilities[sid] = weight
    total = sum(probabilities.values())
    return {sid: value / total for sid, value in probabilities.items()}


def get_urgency(
    service_id, season, building_age, days_since_last_service, region="tucson", rng=None
):
    rng = rng if rng is not None else np.random.default_rng(SEED)
    target = rule_urgency(service_id, season, building_age, days_since_last_service, region)
    return int(np.clip(target + rng.integers(-1, 2), 1, 10))


def generate_interactions(customers_df, n_interactions=3000, seed=SEED):
    if n_interactions < len(customers_df) or customers_df.empty:
        raise ValueError("At least one interaction per customer is required")
    rng = np.random.default_rng(seed)
    counts = np.full(len(customers_df), n_interactions // len(customers_df))
    counts[: n_interactions % len(customers_df)] += 1
    rows = []
    window = (WINDOW_END - WINDOW_START).days + 1
    for (_, customer), count in zip(customers_df.iterrows(), counts, strict=True):
        if count > window:
            raise ValueError("Too many visits for fixed daily observation window")
        dates = sorted(rng.choice(window, size=count, replace=False))
        previous = []
        last_date = pd.Timestamp(customer["member_since"])
        for offset in dates:
            date = WINDOW_START + pd.Timedelta(days=int(offset))
            season = season_for_month(date.month)
            probs = get_service_probabilities(
                customer["property_type"],
                customer["zip_code"],
                season,
                customer["building_age_years"],
                previous,
                customer["region"],
            )
            sid = str(rng.choice(list(probs), p=list(probs.values())))
            days = int((date - last_date).days)
            rows.append(
                dict(
                    customer_id=customer["customer_id"],
                    service_id=sid,
                    service_name=SERVICES[sid][0],
                    date=date.date().isoformat(),
                    season=season,
                    rating=int(np.clip(round(rng.normal(4.1, 0.8)), 1, 5)),
                    urgency_score=get_urgency(
                        sid, season, customer["building_age_years"], days, customer["region"], rng
                    ),
                    days_since_last_service=days,
                    completed=True,
                    repeat_booking=sid in previous,
                )
            )
            previous.append(sid)
            last_date = date
    result = (
        pd.DataFrame(rows)
        .sort_values(["date", "customer_id"], kind="stable")
        .reset_index(drop=True)
    )
    result.insert(0, "interaction_id", [f"I{i + 1:05d}" for i in range(len(result))])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", choices=[*REGIONS, "both"], default="both")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "data")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    customers = generate_customers(region=args.region, seed=args.seed)
    interactions = generate_interactions(customers, seed=args.seed)
    services = generate_services_df()
    for name, frame in [
        ("customers", customers),
        ("interactions", interactions),
        ("services", services),
    ]:
        frame.to_csv(args.output_dir / f"{name}.csv", index=False, lineterminator="\n")
    manifest = dict(
        synthetic=True,
        seed=args.seed,
        region=args.region,
        observation_start="2023-01-01",
        observation_end="2025-12-31",
        customers=len(customers),
        interactions=len(interactions),
        services=len(services),
        generator_version="2.0.0",
        prices="illustrative, not company quotes",
    )
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
