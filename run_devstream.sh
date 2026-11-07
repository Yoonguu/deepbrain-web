#!/usr/bin/env bash
set -euo pipefail
umask 077

cd "$(dirname "$0")"
: "${DEVSTREAM_BASE_URL_8501:?Devstream base URL is required}"

export APP_PUBLIC_ORIGIN="${APP_PUBLIC_ORIGIN:-${DEVSTREAM_EXTERNAL_ORIGIN_8501:-}}"
export MEDICAL_DATA_DIR="${MEDICAL_DATA_DIR:-$(pwd)/data}"

exec "${PYTHON_BIN:-python3}" -m uvicorn backend.devstream:application \
  --host 0.0.0.0 --port "${PORT:-8501}" --workers 1
