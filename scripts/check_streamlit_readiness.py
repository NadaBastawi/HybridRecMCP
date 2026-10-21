"""Exercise actual Streamlit initialization in a clean source copy, without an API."""

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def peak_memory_mib():
    if os.name == "nt":
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
                (name, ctypes.c_size_t)
                for name in (
                    "peak",
                    "working",
                    "paged_peak",
                    "paged",
                    "nonpaged_peak",
                    "nonpaged",
                    "pagefile",
                    "pagefile_peak",
                )
            ]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(
            kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return round(counters.peak / 1024**2, 2)
    import resource

    amount = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(amount / (1024**2 if sys.platform == "darwin" else 1024), 2)


def probe(mode):
    from streamlit.testing.v1 import AppTest

    cache = ROOT / ".cache/demo-model"
    path = cache / "model.pkl"
    if mode == "cold":
        assert not path.exists() and not (ROOT / "models").exists()
    elif mode == "invalid":
        path.write_bytes(b"invalid cached artifact")
    before = path.stat().st_mtime_ns if path.exists() else None
    started = time.perf_counter()
    app = AppTest.from_file(str(ROOT / "demo.py"), default_timeout=120).run()
    initialization = time.perf_counter() - started
    assert not app.exception and not app.error
    artifact_time = path.stat().st_mtime_ns
    assert artifact_time == before if mode == "warm" else artifact_time != before
    app.button[0].click().run()
    assert not app.exception and not app.error and app.metric[0].value == "5"
    first = app.session_state["result"]
    assert all(r["urgency_score"] is None for r in first["recs"])
    rerun = time.perf_counter()
    app.run()
    rerun = time.perf_counter() - rerun
    assert path.stat().st_mtime_ns == artifact_time
    app.selectbox(key="demo_region").set_value("ohio").run()
    assert not app.metric
    app.button[0].click().run()
    assert app.session_state["result"]["inputs"]["region"] == "ohio"
    assert all(r["category"] != "scorpion" for r in app.session_state["result"]["recs"])
    app.radio(key="scenario").set_value("Existing synthetic customer").run()
    assert not app.metric
    app.button[0].click().run()
    assert not app.exception and not app.error and app.metric[0].value == "5"
    app.selectbox(key="demo_region").set_value("tucson").run()
    app.button[0].click().run()
    assert app.session_state["result"]["inputs"]["customer_id"] == "C0001"
    app.radio(key="scenario").set_value("New customer").run()
    app.text_input(key="zip_tucson").set_value("bad").run()
    app.button[0].click().run()
    assert app.error and not app.exception and not app.metric
    assert path.stat().st_mtime_ns == artifact_time
    print(
        json.dumps(
            dict(
                mode=mode,
                initialization_seconds=round(initialization, 3),
                cached_rerun_seconds=round(rerun, 3),
                peak_memory_mib=peak_memory_mib(),
                artifact_bytes=path.stat().st_size,
                verified=True,
            )
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", choices=["cold", "warm", "invalid"])
    parser.add_argument("--output", type=Path, default=ROOT / "reports/streamlit_readiness.json")
    args = parser.parse_args()
    if args.probe:
        probe(args.probe)
        return
    excluded = shutil.ignore_patterns(
        ".git",
        ".venv*",
        ".cache",
        "models",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".env*",
        "secrets.toml",
        "*.zip",
        "*.pkl",
        "logs",
        "*.jsonl",
    )
    with tempfile.TemporaryDirectory(prefix="hybrid-cloud-check-") as temporary:
        source = Path(temporary) / "checkout"
        shutil.copytree(ROOT, source, ignore=excluded)
        env = {
            k: v
            for k, v in os.environ.items()
            if k
            not in (
                "API_KEY",
                "API_BASE",
                "DEMO_MODEL_CACHE_DIR",
                "DEMO_DEFAULT_REGION",
                "SENTRY_DSN",
            )
        }
        env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
        results = []
        for mode in ("cold", "warm", "invalid"):
            run = subprocess.run(
                [
                    sys.executable,
                    str(source / "scripts/check_streamlit_readiness.py"),
                    "--probe",
                    mode,
                ],
                cwd=source,
                env=env,
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=180,
            )
            if run.returncode:
                raise RuntimeError(f"{mode} readiness check failed:\n{run.stdout}\n{run.stderr}")
            results.append(json.loads(run.stdout.strip().splitlines()[-1]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(dict(python=sys.version.split()[0], checks=results), indent=2) + "\n"
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
