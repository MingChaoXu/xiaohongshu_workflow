#!/usr/bin/env bash
set -euo pipefail
CONDA_BIN="$HOME/miniconda3/bin/conda"
DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_NAME="${XHS_PY_ENV:-base}"
exec "$CONDA_BIN" run -n "$ENV_NAME" python "$DIR/bin/run.py" "$@"
