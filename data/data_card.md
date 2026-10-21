# Synthetic data card

Version 2; seed 42; fixed observation window 2023-01-01 through 2025-12-31.
The checked-in default combines 375 Tucson and 125 Ohio profiles, 3,000 completed
simulated visits and ten illustrative services. It contains no real customer data.
No names, addresses, emails, phone numbers or payment information are generated.

## Provenance and assumptions

Everything is generated locally by `generate_data.py`. Prices were retained as
illustrative numeric examples from the original project; they are not company quotes.
Property mix, ZIP grouping, building age distributions, seasonal weights, repeat-visit
weights, ratings and priority targets are hand-authored assumptions. Sources for
broad biological context do not validate these numbers (see regional_assumptions.md).

Customers are synthetic static snapshots: property age is a fixed scenario attribute,
not a measured age at each visit. Membership precedes all visits. Each customer's
visits are generated in date order without duplicate days; history, repeat flags and
days since the prior visit use only earlier events. All generated bookings are completed;
cancellations and non-booking exposures are not modeled.

## Fields

- customers.csv: customer_id; property_type; five-digit ZIP string; region;
  building_age_years; illustrative desert flag; commercial flag; location_supported;
  member_since; num_units. `is_older_neighborhood` is retained as a false compatibility
  field, not inferred from unverified neighborhood demographics or used by the model.
- interactions.csv: unique interaction_id; customer_id; service_id/name; date;
  date-consistent season; integer rating 1–5; synthetic urgency 1–10;
  actual days_since_last_service; completed; repeat_booking based on prior events.
- services.csv: service_id/name; illustrative price_usd; category;
  suitable_residential/commercial; descriptive peak_season label.
- manifest.json: generation seed, window, row counts and version.

## Constraints and limitations

Commercial management is not suggested for residential properties. The Ohio scenario
excludes scorpion service. These are conservative demonstration catalog policies, not
legal applicability or a statement that other services are suitable in every case.
Treatment-labeled services require assessment, not automatic application. No inspection
result or infestation evidence is generated.

Ratings are noisy and mostly positive, and missing bookings are not dislike labels.
The tiny catalog makes top-five hit rate generous. The profile/rule baselines know
parts of the same assumptions used by generation; their scores are not independent
scientific validation. No result establishes real-world demand, risk, causal lift,
customer benefit or business return. Changing the generator changes the task itself.

Regenerate: `python generate_data.py` (default both), or select `--region tucson` /
`--region ohio`. Run `python evaluate.py` and `python train.py` afterward. Data quality
checks run in `data_utils.py` and automated tests. The original CSVs remain available
in Git history, rather than being presented as corrected chronological data.
