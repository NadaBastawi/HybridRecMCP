"""Manual monitoring diagnostic; importing it never writes prediction records."""

import json

from monitoring.drift_detector import get_drift_report
from monitoring.logger import PredictionLogger

if __name__ == "__main__":
    logger = PredictionLogger()
    try:
        print(json.dumps(get_drift_report(logger.get_recent_logs()), indent=2))
    finally:
        logger.close()
