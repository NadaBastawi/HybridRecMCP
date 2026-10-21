# Legacy compatibility note

The historical monitoring smoke script is now read-only and protected by a main guard.
Use `python -m pytest tests/test_monitoring.py` for deterministic regression tests.
