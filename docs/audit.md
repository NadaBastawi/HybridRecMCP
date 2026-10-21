# Technical audit

Baseline: `38e1cc43b78e4163d019fb278e105b9e22e4bfc6`, inspected 21 October 2026.
This audit covers all tracked source, tests, configuration, CSV data, documentation,
and all 27 EDA notebook cells. Changes and validation are recorded in the final report.

| Severity | Verified baseline defect | Correction target |
|---|---|---|
| High | Evaluation fits on every interaction before selecting a holdout; reset indices select the wrong training rows and the computed train frame is unused. Hit rate is called Precision@5; NDCG is only claimed. | Split before every fit; temporal validation/test and customer-disjoint cold-start evaluation; correct metrics and baselines. |
| High | MCP reads `recommendation_score` instead of `score`, treats a services list as a mapping, sends no authentication, and labels all errors successful. | Official SDK, validated shared contracts, authenticated HTTP, protocol/client regression tests. |
| High | API silently accepts unauthenticated recommendations when API_KEY is unset. | Require a non-placeholder secret at startup; compare securely. |
| High | Container runtime omits dotenv and Sentry imports; build/runtime ML versions differ. | Shared locked runtime dependencies and artifact compatibility checks. |
| High | Generation uses unseeded Faker/current date, visits are out of chronological order and may precede membership; history can include future events. | Fixed observation window, isolated seeded RNGs, sorted per-customer events, quality validation. |
| Medium | Property LabelEncoder imposes artificial ordinal similarity; unknown profiles fail urgency encoding; SVD zero cells act as negative ratings and components are almost full rank. | One-hot profile transformation; missing-aware rating completion; adaptive rank and cold-start fallback. |
| Medium | Cold-start ranks urgency only; existing ranking ignores suitability flags and region; commercial services can reach homes. | Separate relevance/urgency; explicit repeat policy; catalog and region eligibility. |
| Medium | API accepts invalid seasons, property types, ranges, null optionals and negative top_n, leading to server errors or unexpected results. | Shared constrained Pydantic schemas and regression tests. |
| Medium | Hardcoded Sentry DSN, default PII and full trace sampling. | Optional environment configuration, PII off, scrub payloads. |
| Medium | Monitoring imported but never called. Two incompatible log formats; drift fabricates production features and has no corresponding reference features, often returning OK with no analysis. PSI mishandles empty/out-of-range bins and zeros. | One privacy-conscious JSONL schema, real feature logging, explicit insufficient-data state and robust PSI. |
| Medium | Azure workflow builds but fails at Login to Azure; app deployment is skipped. Job logs are unavailable (404). | Manual gated deploy workflow with preflight and explicit OIDC setup instructions; no cloud changes. |
| Medium | Tests can silently skip API imports; no MCP/evaluation regression coverage; monitoring test runs at import. | Fail required imports; real protocol tests; meaningful data/model/API/monitoring regressions. |
| Medium | README and plan describe nonexistent folders and unsupported metrics, model performance, financial impact, ownership/production implications. Notebook has broken CSV paths, duplicate cells and stale outputs. | Accurate documentation, cleared and repaired EDA, business proposal and demo script. |
| Low | Development/notebook dependencies are installed in production, duplicate httpx, global warning suppression and random seeds. | Separate dependency groups, local RNGs, lint/format/type checks. |

No evidence establishes company authorization or relationships between similarly named
businesses. Tucson remains the default; any Ohio scenario must be independently labeled.
All prices and regional weights are illustrative assumptions, not verified company data.

## Quantified original data defects

The original 3,000 rows contained 926 visits before membership and 1,817 rows generated
after at least one later-dated visit for the same customer. Replacing chronology required
regenerating the synthetic dataset; the original data remains in Git history.
