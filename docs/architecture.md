# Architecture and model lifecycle

## Layout

```text
HybridRecMCP/
  config/regions.json        shared illustrative region configuration
  domain.py                  profile, eligibility and simulator baseline rules
  generate_data.py           deterministic synthetic data CLI
  data_utils.py              CSV validation and fingerprints
  recommender.py             content, iterative SVD, urgency, hybrid classes
  evaluate.py                temporal validation/test + cold-user evaluation
  train.py                   explicit full-data deployment-artifact training
  schemas.py / settings.py   shared contracts and safe environment configuration
  main.py                    authenticated FastAPI factory and lifespan
  server.py                  official MCP SDK stdio -> authenticated HTTP
  demo.py                    standalone local/public Streamlit presentation
  model_store.py             private, verified, locked demo artifact cache
  explanations.py            deterministic profile/rule context and staff questions
  monitoring/                rotating logs and real-feature drift diagnostics
  tests/                     data/model/evaluation/API/MCP/UI/monitoring regressions
  scripts/                   notebook check and explicit Azure source-start script
  reports/evaluation.json    reproducible evaluation measurements
  docs/                      audit, limitations, business proposal and walkthrough
```

## Data and training

The generator uses local seeded RNGs and a fixed date window. All visits are completed,
chronological, post-membership and compatible with the catalog/region. Repeat flags and
visit intervals use prior events only. Data validation runs before training/evaluation.

Evaluation reserves whole cold customers, then splits the warm data globally by date.
Each candidate fits content transforms, affinities, SVD factors and urgency exclusively
on training data. Validation selects relevance weights and rank. A final evaluation
model fits train+validation and scores the untouched future test period and cold cohort.
The cold cohort's profiles never fit feature transformations or affinities.

`train.py` separately fits the chosen architecture on all synthetic data for presentation.
It writes a versioned local joblib envelope atomically, recording data/config hash,
Python/ML versions, evaluation-report hash and model-code hash. It is not the evaluation model. Model artifacts
are ignored by Git and may be loaded only from trusted builds. API startup checks
metadata and fails on mismatches rather than using stale data or silently retraining.

## Serving

FastAPI has no import-time model fitting or outbound telemetry. Lifespan validates the
key, loads the model once, and opens the rotating prediction logger. Requests use
strict shared schemas and apply catalog suitability. Recommendations expose stable
`score`, `urgency_score`, `urgency_label`, `price_basis`, explanation and disclaimer fields.

MCP uses the official 1.x SDK's lifecycle, framing and schema support. Three tools
forward the configured secret to a fixed configured API base. Remote HTTP is rejected;
use HTTPS outside localhost. Returned JSON is validated against API contracts. Transport,
authentication and response failures become MCP errors without raw URLs, bodies or keys.
The tests use an actual SDK client, subprocess stdio and local Uvicorn HTTP service.

Streamlit runs the Python engine in-process without API calls or credentials. On
first initialization it validates the shipped data/evaluation selection and trains
only if its server-owned cache is missing or incompatible. It never runs evaluation
or regenerates datasets. A thread/process lock and atomic file replacement protect
concurrent initialization. The manifest's origin, exact metadata and byte hash are
verified before local deserialization; this relies on a trusted server filesystem,
not on treating pickle as safe for uploads. Streamlit caches the verified engine across
reruns; a warm process restart can reuse the disk artifact. Ephemeral storage loss
triggers deterministic preparation again. The API separately uses explicitly trained
`models/` artifacts and remains fail-closed with mandatory authentication.

Unknown new-customer service timing is explicit `None`: relevance ordering is unchanged,
urgency is not predicted, and score/label become null/UNKNOWN. Existing numeric defaults
remain compatible. Explanations describe documented profile/catalog rules, not model
attributions. UI input fingerprints remove stale results after changes. No public
administration, uploads, booking or customer communications occur. See the deployment
guide for the public-hosting boundary and optional separate Azure backend.

## Observability

Every successful API recommendation emits one JSONL row per recommended service with
coarse features, scores and timestamp. Customer IDs, ZIPs, emails, names, keys and
unrestricted request data are excluded. Logs rotate at 1 MB with three backups.
`/monitoring` compares the first and second halves of retained recent logs. It requires
at least 20 samples per side, handles empty/constant/out-of-range PSI distributions,
and reports INSUFFICIENT_DATA rather than fabricating features or declaring OK without
analysis. Within-request rows are correlated: diagnostics are descriptive, not inferential
proof of drift or accuracy. A training-reference/production baseline and distributed
telemetry are future extensions.

Sentry is optional, environment-configured and strips request/user/breadcrumb context;
PII, locals and tracing are disabled by default. Sentry transmission was not exercised.
