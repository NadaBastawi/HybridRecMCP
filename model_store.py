"""Private local demo cache. Visitors cannot upload or choose model artifacts."""

import hashlib
import json
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from domain import ROOT
from recommender import HybridRecommender
from train import artifact_metadata, train_from_data, validated_selection

_thread_lock = threading.Lock()


def demo_cache_dir():
    configured = os.getenv("DEMO_MODEL_CACHE_DIR")
    return Path(configured).expanduser().resolve() if configured else ROOT / ".cache/demo-model"


@contextmanager
def initialization_lock(cache, timeout=120):
    """Serialize threads and processes; leave the lock inode in place for waiters."""
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = cache / "prepare.lock"
    if lock_path.is_symlink():
        raise ValueError("Cache lock cannot be a symlink")
    with _thread_lock, lock_path.open("a+b") as stream:
        stream.seek(0, 2)
        if not stream.tell():
            stream.write(b"0")
            stream.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Model initialization is still busy") from None
                time.sleep(0.05)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _verified_local_model(cache, metadata):
    """Check manifest compatibility and bytes BEFORE trusted local deserialization.

    The directory is server-owned. Hashes detect corruption, not a malicious server
    administrator who can replace both files. Never use this for uploaded models.
    """
    path, manifest = cache / "model.pkl", cache / "manifest.json"
    if path.is_symlink() or manifest.is_symlink():
        return None
    if not path.is_file() or not manifest.is_file():
        return None
    if path.stat().st_size > 16_000_000 or manifest.stat().st_size > 16_000:
        return None
    try:
        record = json.loads(manifest.read_text(encoding="utf-8"))
        if (
            record.get("origin") != "local-deterministic-training-v1"
            or record.get("metadata") != metadata
        ):
            return None
        if hashlib.sha256(path.read_bytes()).hexdigest() != record.get("sha256"):
            return None
        model = HybridRecommender.load(path, metadata)
        if not isinstance(model, HybridRecommender):
            return None
        return model
    except Exception:
        # Do not expose deserialization exceptions/paths; regenerate from approved CSVs.
        return None


def prepare_demo_model(cache_dir=None):
    """Load a verified private artifact or rebuild it from the committed demo data."""
    cache = Path(cache_dir) if cache_dir is not None else demo_cache_dir()
    if cache.is_symlink():
        raise ValueError("Model cache cannot be a symlink")
    # Fail if the report/data are incompatible; never invent replacement weights.
    validated_selection(ROOT / "data", ROOT / "reports/evaluation.json")
    metadata = artifact_metadata(ROOT / "data")
    with initialization_lock(cache):
        loaded = _verified_local_model(cache, metadata)
        if loaded is not None:
            return loaded
        model = train_from_data()
        with tempfile.TemporaryDirectory(dir=cache, prefix=".prepare-") as temporary:
            artifact = Path(temporary) / "model.pkl"
            model.save(artifact, metadata)
            record = dict(
                origin="local-deterministic-training-v1",
                metadata=metadata,
                sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
            )
            manifest = Path(temporary) / "manifest.json"
            manifest.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
            os.replace(artifact, cache / "model.pkl")
            os.replace(manifest, cache / "manifest.json")
        return model
