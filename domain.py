"""Shared, explicitly illustrative regional and service rules."""

import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REGIONS = json.loads((ROOT / "config/regions.json").read_text(encoding="utf-8"))
PROPERTY_TYPES = (
    "residential_house",
    "residential_apartment",
    "commercial_restaurant",
    "commercial_office",
    "commercial_warehouse",
    "mobile_home",
)
SEASONS = ("winter", "spring", "summer", "fall")
DISCLAIMER = (
    "Independent, unofficial proof of concept using synthetic data. Prices are illustrative. "
    "Recommendations suggest staff follow-up, not confirmed infestations or required treatments. "
    "Urgency is a simulated priority estimate, not a professional assessment."
)


def season_for_month(month: int) -> str:
    return SEASONS[(month % 12) // 3]


def build_profile(
    property_type: str, zip_code: str, building_age_years: int, region: str = "tucson"
) -> dict:
    if region not in REGIONS:
        raise ValueError("Unsupported region")
    if property_type not in PROPERTY_TYPES:
        raise ValueError("Unsupported property type")
    if not re.fullmatch(r"[0-9]{5}", str(zip_code)):
        raise ValueError("ZIP code must contain five digits")
    if not 0 <= building_age_years <= 200:
        raise ValueError("Building age must be between 0 and 200")
    config = REGIONS[region]
    known = any(str(zip_code).startswith(p) for p in config["zip_prefixes"])
    return {
        "property_type": property_type,
        "zip_code": str(zip_code),
        "building_age_years": building_age_years,
        "region": region,
        "is_commercial": property_type.startswith("commercial_"),
        "is_desert_adjacent": str(zip_code) in config["scorpion_scenario_zips"],
        "is_older_neighborhood": False,
        "location_supported": known,
    }


def eligible(service: dict, profile: dict) -> bool:
    flag = "suitable_commercial" if profile["is_commercial"] else "suitable_residential"
    if not bool(service.get(flag, True)):
        return False
    return service.get("category") != "scorpion" or REGIONS[profile["region"]]["scorpion_enabled"]


def rule_urgency(
    service_id: str,
    season: str,
    building_age: int,
    days_since_last_service: int,
    region: str = "tucson",
) -> float:
    """Noise-free synthetic target rule; not a validated pest-risk model."""
    base = 7 if service_id in ("S03", "S04", "S10") else 5
    if season in REGIONS[region]["termite_peak_seasons"] and service_id in ("S02", "S03"):
        base += 1
    if season == "summer" and service_id == "S06" and region == "tucson":
        base += 2
    if building_age > 30 and service_id in ("S02", "S03"):
        base += 1
    base += int(days_since_last_service > 365) + 2 * int(days_since_last_service > 730)
    return float(np.clip(base, 1, 10))


def profile_prior(profile: dict, service_id: str, season: str = "summer") -> float:
    """Simple hand-authored baseline, also used by the simulator; not independent evidence."""
    prop = profile["property_type"]
    weights = {
        "S01": 0.35,
        "S02": 0.12,
        "S03": 0.06,
        "S04": 0.05,
        "S05": 0.08,
        "S06": 0.05,
        "S07": 0.10,
        "S08": 0.4,
        "S09": 0.16,
        "S10": 0.03,
    }
    if service_id in ("S02", "S03"):
        weights[service_id] += 0.12 * (profile["building_age_years"] > 20)
        weights[service_id] += 0.10 * (season in REGIONS[profile["region"]]["termite_peak_seasons"])
    if prop == "residential_apartment":
        weights.update(S04=0.20, S07=0.20)
    if prop in ("commercial_restaurant", "commercial_warehouse"):
        weights.update(S05=0.30, S07=0.30)
    if profile["is_commercial"]:
        weights["S01"] = 0.15
    if profile["is_desert_adjacent"]:
        weights["S06"] = 0.30
    return weights[service_id]
