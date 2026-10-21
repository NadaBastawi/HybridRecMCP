#!/bin/sh
# Explicit training on the target runtime; API import itself never trains.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
# Fail closed before spending time training. Never print environment values.
python -c 'from settings import Settings; Settings.from_env()'
python train.py --data-dir "${DATA_DIR:-data}" --model-dir "${MODEL_DIR:-models}"
exec python -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
