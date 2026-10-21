# Deployment notes

## Primary public demonstration: Streamlit

Use root `demo.py`, root `requirements.txt` (the demo lock), and Python 3.12 on
Streamlit Community Cloud. It operates in-process without FastAPI or API keys and
prepares a private model cache from the committed synthetic data. See the exact
[Streamlit deployment instructions](streamlit_deployment.md) and
[public presentation checklist](public_demo_checklist.md). No public deployment is
claimed. The following API/Docker/Azure paths are independent.

## Local verified target

Python 3.12, pinned dependencies, generated data, explicit evaluation/training and
localhost Uvicorn/Streamlit. Consult the validation report for exact completed checks.
Do not infer deployment success from source code or an old CI badge.

## Docker

```sh
docker build -t hybridrecmcp:local .
docker run --rm -p 127.0.0.1:8000:8000 --env-file .env hybridrecmcp:local
```

`.env` must have a non-placeholder API_KEY. The multi-stage image installs one locked
runtime dependency set from `requirements-api.txt` (including dotenv/Sentry/MCP), explicitly trains the artifact
in the builder, copies the same environment into the runtime stage, runs as a nonroot
user and exposes a health check. No demo/notebook/test tooling is required in the runtime
image. A base Python patch change requires rebuilding artifacts. A supplied .env with
host-only absolute DATA_DIR/MODEL_DIR/LOG_DIR paths must be adjusted for `/app`.

The local Docker client exists but no engine is running (missing docker_engine named
pipe). No successful image build or container run is claimed locally. The revised CI
contains build/start/health steps; consult the current pull request checks for its
actual remote result. Pin the base-image digest for a release after
choosing and verifying a supported image in the deployment environment.

## Azure blocker and investigation

At baseline commit 38e1cc43, [run 31852813788](https://github.com/NadaBastawi/HybridRecMCP/actions/runs/31852813788)
built successfully, failed at **Login to Azure**, and skipped deployment. Downloaded
job logs were unavailable (GitHub 404), so an exact tenant/federation/credential cause
cannot be established. It is not evidence of an application failure or successful
hosting. No Azure account/subscription/resource access was available for this work.

The replacement workflow is **manual only**, requires an explicit deploy input,
uses an `azure-demo` environment, checks configuration before login, and uses standard
OIDC identifiers rather than embedding actual credentials. Before an authorized run,
an administrator must configure:

- GitHub environment secrets AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID.
- Environment variable AZURE_WEBAPP_NAME for an existing Linux Python 3.12 App Service.
- Microsoft Entra application or user-assigned identity with a GitHub federated
  credential: issuer `https://token.actions.githubusercontent.com`, audience
  `api://AzureADTokenExchange`, exact case-sensitive subject
  `repo:NadaBastawi/HybridRecMCP:environment:azure-demo`. A branch-based subject does
  not match this environment-based job. Set the three identifier secrets from that
  actual identity, tenant and subscription; no resource identifiers are supplied here.
- Assign the identity a deployment role scoped to the existing App Service (for
  example Website Contributor where appropriate); a subscription owner must review
  actual permissions. Configure GitHub environment approval rules as desired.
- App Service API_KEY, `SCM_DO_BUILD_DURING_DEPLOYMENT=true`, writable model/log paths,
  and the documented startup command. Do not store the application key in source.
- App Service Linux stack **Python 3.12**, startup command
  `sh scripts/azure_start.sh`, Health check path `/health`, HTTPS enabled.
  Keep `PORT` unset for the default 8000 unless the hosting configuration explicitly
  requires another value. `API_KEY` must be a unique non-placeholder secret of at
  least 16 characters. For persistent writable paths set `MODEL_DIR=/home/hybrid-models`
  and `LOG_DIR=/home/hybrid-logs` in App Service application settings; omit DATA_DIR
  to use shipped CSVs. SENTRY_DSN is optional, not needed for the demo.
- Oryx installs archive-root `requirements.txt`, which the packaging script copies
  from `requirements-api.txt`; it includes only `requirements.lock`. Source packaging
  is an explicit allowlist, so local caches, secrets, models and dashboard files
  cannot accidentally enter the backend archive.

Source deployment uses `scripts/azure_start.sh`: explicitly train on the target Python
runtime after validating API_KEY, then launch one Uvicorn worker. It resolves its
own project directory and honors DATA_DIR, MODEL_DIR and PORT. Thus artifact package/Python versions match;
API import itself never trains. This is an uncomplicated demo strategy, not a production
training scheduler. Training occurs on each restart; choose an offline managed-artifact
pipeline, persistence/rollbacks and startup budgets for a real pilot. Sentry remains opt-in.

External credentials, OIDC trust, subscription permissions and resources cannot be
repaired by source refactoring alone. No Azure workflow was dispatched, cloud resource
modified or production deployment attempted. Ordinary CI needs no Azure credentials.

After an administrator completes the settings above and explicitly authorizes deployment,
open GitHub **Actions → Manual Azure App Service deployment → Run workflow**, select
the reviewed branch and check `authorize_deploy`. The job has only contents:read and
id-token:write permissions. Tests and training precede allowlisted packaging and OIDC
login. The deploy action sets the startup command; a subsequent check retries `/health`
and verifies unauthenticated `/services` returns 401. This confirms readiness/authentication
boundaries, not an authenticated business interaction; test one securely afterward.
Do not dispatch the workflow merely to diagnose missing credentials. Review App Service
startup/build logs privately if readiness fails. Source changes do not repair Entra
federation or missing roles. The original authentication cause remains uncertain.

References: [Azure OIDC GitHub Actions setup](https://learn.microsoft.com/en-us/azure/app-service/deploy-github-actions?tabs=openid)
and [Python startup configuration](https://learn.microsoft.com/en-us/azure/app-service/configure-language-python#customize-startup-command).

## Dependency maintenance

`requirements.in` defines API/MCP dependencies; demo/dev inputs extend it. The `.lock`
files pin transitive packages with platform markers using uv's universal resolver.
Recompile with Python 3.12 and review/test upgrades before using the resulting artifact.
Locking improves repeatability, not long-term security certification or immutable OS
reproducibility. Mypy is scoped to schemas/settings; no full-repository strict typing
claim is made.
