"""Deterministic scenario context, never invented model feature attributions."""

from domain import REGIONS


def explain_service(service_id, category, profile, season, days):
    prop = profile["property_type"]
    age = profile["building_age_years"]
    contexts = {
        "general": (
            "A routine review is an option across the supported property types.",
            "Have you noticed pest activity near doors, windows or other entry points?",
        ),
        "bed_bug": (
            "The demo gives apartment profiles additional bed-bug assessment context."
            if prop == "residential_apartment"
            else "This assessment is a discussion option; the profile does not establish bed-bug activity.",
            "Have occupants reported signs that a specialist should inspect?",
        ),
        "rodent": (
            "The restaurant/warehouse scenario includes a greater illustrative rodent-service weight."
            if prop in ("commercial_restaurant", "commercial_warehouse")
            else "A rodent review can be discussed if there are reported signs; none are recorded in this profile.",
            "Have you noticed droppings, gnaw marks or possible access points?",
        ),
        "scorpion": (
            "This ZIP belongs to the demo's illustrative Tucson desert-scenario grouping."
            if profile["is_desert_adjacent"]
            else "Scorpion services are in the Tucson demo catalog; no local activity is confirmed for this property.",
            "Have scorpions actually been observed around the property?",
        ),
        "ant_roach": (
            "The apartment/restaurant/warehouse scenario includes an illustrative ant-and-cockroach service emphasis."
            if prop in ("residential_apartment", "commercial_restaurant", "commercial_warehouse")
            else "An inspection discussion can focus on reported signs around food, water and entry points.",
            "Where and when have ants or cockroaches been observed?",
        ),
        "commercial": (
            "This is a commercial property, so the commercial-management catalog option is eligible.",
            "Which operating areas or access times should a service review consider?",
        ),
        "preventive": (
            "Preventive follow-up is a recurring-service option; an elapsed interval alone does not prove a pest problem.",
            "Is there a current preventive plan, and when was it last reviewed?",
        ),
        "emergency": (
            "This is a priority inspection discussion option, not confirmation that an emergency exists.",
            "What has been observed that would justify requesting a prompt professional assessment?",
        ),
    }
    if category == "termite":
        if service_id == "S02":
            context = (
                f"At {age} years, this property falls into the demo's older-building scenario."
                if age > 20
                else "A termite inspection can be discussed without assuming an infestation."
            )
            question = (
                "When was the property last inspected for termites, and were any findings recorded?"
            )
        else:
            context = "A treatment consultation requires inspection evidence; the property profile alone does not justify treatment."
            question = "Has a qualified inspection confirmed termite activity or damage?"
        if season in REGIONS[profile["region"]]["termite_peak_seasons"]:
            context += f" {season.title()} is an illustrative seasonal setting in this region."
    else:
        context, question = contexts.get(
            category,
            (
                "This catalog option may be discussed after confirming the property's circumstances.",
                "What observations or previous inspection findings should staff review?",
            ),
        )
    if days is None:
        context += " Previous service timing is unknown, so priority is not estimated."
    else:
        context += f" Separate simulated priority considers {season} and the supplied {days}-day service interval."
    if not profile.get("location_supported", True):
        context += " ZIP outside demo geography; location evidence is limited."
    return context, question
