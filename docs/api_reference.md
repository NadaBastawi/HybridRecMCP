# API reference

Base URL: http://127.0.0.1:8000. Set the same secret in `.env` and caller configuration.
The service will not start without a non-placeholder API_KEY of at least 16 characters
and a compatible trained local artifact. See `/docs` for generated OpenAPI schemas.

| Method and route | Authentication | Response |
|---|---|---|
| GET / | Public | Overview and independent-project disclaimer |
| GET /health | Public | status, model_loaded, model_version, synthetic_data |
| GET /services | X-API-Key | List of ten service objects with suitability and illustrative price_basis |
| POST /recommend | X-API-Key | Shared RecommendResponse, customer_type=existing |
| POST /recommend/new-customer | X-API-Key | Shared RecommendResponse, customer_type=new |
| GET /monitoring | X-API-Key | Status, sample counts and actual-feature PSI/KS diagnostics |

`/recommend`: customer_id matching C followed by 4–8 digits; optional season (winter,
spring, summer, fall), integer days_since_last_service 0–36500 (default 180), integer
top_n 1–10 (default 5). Unknown valid-format IDs return 404.

`/recommend/new-customer`: property_type from residential_house, residential_apartment,
commercial_restaurant, commercial_office, commercial_warehouse, mobile_home; ZIP as a
five-digit string; integer building_age_years 0–200. Optional region tucson (default)
or ohio; season; days_since_last_service (default 365 when omitted, explicit null means
unknown service history); top_n. ZIP format is validated;
geographical existence is not. Outside-demo ZIPs carry limited-location explanations.

Responses include customer_id (null for new), customer_type, safe profile fields,
recommendations, model_version, synthetic_data and disclaimer. Each recommendation has
service_id/name/category, illustrative price_usd/price_basis, relevance score 0–1,
urgency_score 1–10 (or null for unknown timing), urgency_label (LOW/MEDIUM/HIGH/UNKNOWN),
explanation, follow_up_question and requires_assessment=true. Relevance
is not a calibrated probability. Priority does not predict a service deadline.

Other optional fields have defaults but reject null. Extra fields and unsupported enums
are rejected. Invalid inputs return 422; missing/wrong keys return 401. Suitability may
reduce returned count below requested top_n. Repeated services are permitted by design.
No endpoint writes customer bookings or dispatches treatment. Do not expose the demo API
publicly without TLS, request limits, reviewed authorization and operational hardening.
