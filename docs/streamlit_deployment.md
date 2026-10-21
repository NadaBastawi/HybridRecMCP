# Streamlit Community Cloud demonstration

Status: repository prepared for deployment; no public URL has been published or verified.
Visitors need only a browser. FastAPI, an API key and an Azure subscription are not required.

## Publish after reviewing the local changes

1. Review this working tree, commit it and push to `NadaBastawi/HybridRecMCP` with your
   authorization. These operations have not been performed by this task. The existing
   remote `main` branch will not contain the improvements until then.
2. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) and authorize
   access to the repository if necessary. Select **Create app / Deploy from GitHub**.
3. Select repository **NadaBastawi/HybridRecMCP**, branch **main** (after the reviewed
   changes reach that branch), main file **demo.py** at the repository root.
4. Open **Advanced settings** and select **Python 3.12**. Local verification uses
   Python 3.12.3; the hosting platform controls its 3.12 patch version. Models are
   prepared on the target runtime, so local pickle files are unnecessary.
5. No secrets are required. To show Ohio first, optionally put the following non-secret
   setting in the Advanced settings Secrets field:

   ```toml
   DEMO_DEFAULT_REGION = "ohio"
   ```

   The app also accepts an environment variable of the same name. Allowed values are
   `ohio` and `tucson`; the fallback is Tucson. The two regions are independent examples.
   Do not copy `.env`, `API_KEY`, Azure credentials or local filesystem paths here.
6. Select **Deploy** and wait for installation and initialization. Copy the URL issued
   by Streamlit; no hosted address is assumed in this documentation.
7. Open that actual URL in a private browser window. Generate a new-customer result
   with Unknown history; switch to Ohio, then generate an existing-customer result.
   Verify five cards, staff questions, separate priority labels, footer link and
   visible synthetic-data/illustrative-price disclosures. Changing inputs must clear
   previous results. Complete [the public checklist](public_demo_checklist.md).

Only mark the demonstration publicly verified after these interactions work at the
hosted URL. `http://127.0.0.1:8501` is a local address and cannot be shared as a public demo.

## Dependencies and startup

Community Cloud searches the entry-point directory and repository root for supported
dependency files. Root `requirements.txt` selects the pinned `requirements-demo.lock`;
it does not rely on the host discovering a custom `requirements-demo.txt` filename.
Avoid adding higher-priority package-manager files without reviewing that selection.
See [Streamlit's dependency rules](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
and [deployment settings](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

API/Docker use `requirements-api.txt` and `requirements.lock`; development tooling uses
`requirements-dev.txt`. Demo dependencies extend the common runtime lock inputs, so
some API libraries are installed but no API process is started or contacted.

Streamlit controls public networking and ports; committed config has no localhost
binding or fixed port. It preserves the light/green theme and suppresses visitor-facing
tracebacks with `showErrorDetails="none"`. The app also applies that strict mode
programmatically because legacy `false` still exposes stack traces. Keep platform
security defaults, including XSRF protection.

The first initialization validates committed CSVs and the existing evaluation report,
then fits the existing deterministic pipeline with its selected weights. It does not
evaluate or regenerate datasets. `st.cache_resource` reuses the engine across reruns.
A private `.cache/demo-model` artifact and manifest allow subsequent process restarts
to load without retraining. Compatibility includes data/config/code, evaluation bytes,
Python and ML package versions; size, origin marker and SHA256 are checked before
loading. Missing, corrupt or stale artifacts are rebuilt under a thread/process lock.
An incompatible evaluation report causes a controlled initialization failure.

This cache is server-owned and never accepts uploads. A checksum detects corruption,
not an attacker who controls both model and manifest. Do not point
`DEMO_MODEL_CACHE_DIR` at an untrusted/shared upload directory. That optional environment
variable is for operator-controlled writable storage only; omit it on Community Cloud.
The ignored older `models/torco_recommender.pkl` is reserved for explicit backend builds.

## Local rehearsal and readiness

From the repository root with Python 3.12:

```sh
python -m pip install -r requirements.txt
python -m streamlit run demo.py --server.address 127.0.0.1 --server.port 8501
```

Open `http://127.0.0.1:8501`. No API key, manual model upload, evaluation command or
backend server is needed. The committed data and evaluation report must be present.

```sh
python scripts/check_streamlit_readiness.py
```

This uses a clean temporary source copy with no `.env`, model or cache and no API
configuration. It executes actual training/AppTest, then separate warm and corrupt-cache
restart checks, both regions, new/existing recommendations and invalid ZIP handling.
Timing and process peak-memory measurements appear in `reports/streamlit_readiness.json`.
These are local measurements, not hosting performance guarantees. Normal CI also has
a dedicated job installing only root requirements before this probe.

## Hosting limitations, updates and troubleshooting

Free hosting can sleep after inactivity, impose resource limits, delay startup and
discard local storage. A wake/reboot may rebuild the private cache. Check current
[Community Cloud management guidance](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)
for current limits. Do not promise an availability SLA or persistent storage.

- Installation error: confirm root `demo.py`, Python 3.12 and the committed demo lock.
  Review host build logs as the owner; do not paste credentials into issues.
- Controlled initialization error: check that all CSVs, `config/regions.json` and the
  compatible `reports/evaluation.json` were pushed. Do not fabricate replacement
  weights or upload an arbitrary pickle. Reboot after correcting the source/config.
- Stale/corrupt private cache: the next process initialization rebuilds it. Reruns
  normally reuse the already verified in-memory resource. An operator can reboot the
  hosted app; visitors have no retraining or administrative control.
- Wrong default region: configure `DEMO_DEFAULT_REGION`, then reboot. Visitors can
  always select either region. An unsupported value safely falls back to Tucson.
- Following later authorized commits to the selected branch, review the automatic app
  update and repeat the public recommendation smoke test. Dependency/Python changes
  require particular attention to rebuild logs and artifact compatibility.

Azure FastAPI hosting is an optional independent deployment; see [deployment notes](deployment.md).
