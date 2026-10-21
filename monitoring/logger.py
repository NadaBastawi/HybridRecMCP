"""Privacy-conscious, rotating JSONL prediction telemetry."""

import json
import logging
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

SAFE_CONTEXT = {
    "property_type",
    "building_age_years",
    "region",
    "season",
    "days_since_last_service",
}


class PredictionLogger:
    def __init__(self, log_dir="monitoring/logs"):
        self.path = Path(log_dir) / "predictions.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handler = RotatingFileHandler(
            self.path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        self.handler.setFormatter(logging.Formatter("%(message)s"))

    def log_prediction(self, customer_id, service_id, score, urgency, context=None, timestamp=None):
        # Deliberately omit IDs, names, ZIPs, email, secrets and unrestricted context.
        entry = dict(
            timestamp=timestamp or datetime.now(UTC).isoformat(),
            service_id=service_id,
            score=float(score),
            urgency_score=float(urgency) if urgency is not None else None,
            **{key: value for key, value in (context or {}).items() if key in SAFE_CONTEXT},
        )
        record = logging.LogRecord(
            "predictions", logging.INFO, "", 0, json.dumps(entry, allow_nan=False), (), None
        )
        self.handler.handle(record)

    def get_recent_logs(self, hours=24):
        cutoff = datetime.now(UTC).timestamp() - hours * 3600
        rows = []
        for path in reversed(
            [self.path, *[self.path.with_name(self.path.name + f".{i}") for i in range(1, 4)]]
        ):
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    entry = json.loads(line)
                    if datetime.fromisoformat(entry["timestamp"]).timestamp() >= cutoff:
                        rows.append(entry)
                except (ValueError, KeyError, TypeError):
                    continue
        return rows

    def close(self):
        self.handler.close()
