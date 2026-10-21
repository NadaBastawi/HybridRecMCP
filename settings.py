"""Environment-only application configuration with secure defaults."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from domain import ROOT


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    data_dir: Path = ROOT / "data"
    model_dir: Path = ROOT / "models"
    log_dir: Path = ROOT / "monitoring/logs"
    sentry_dsn: str = field(default="", repr=False)

    def __post_init__(self):
        if len(self.api_key) < 16 or self.api_key.lower() in (
            "your-api-key-here",
            "change-me-before-use",
        ):
            raise ValueError("API_KEY must be a non-placeholder secret with at least 16 characters")

    @classmethod
    def from_env(cls):
        load_dotenv(ROOT / ".env", override=False)

        def path(name, default):
            value = Path(os.getenv(name, str(default)))
            return value if value.is_absolute() else ROOT / value

        return cls(
            api_key=os.getenv("API_KEY", ""),
            data_dir=path("DATA_DIR", ROOT / "data"),
            model_dir=path("MODEL_DIR", ROOT / "models"),
            log_dir=path("LOG_DIR", ROOT / "monitoring/logs"),
            sentry_dsn=os.getenv("SENTRY_DSN", ""),
        )


def scrub_sentry(event, hint):
    event.pop("user", None)
    event.pop("request", None)
    event.pop("breadcrumbs", None)
    return event
