#!/usr/bin/env bash
set -euo pipefail
umask 077
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHON_BIN="${PYTHON_BIN:-$(dirname "$project_dir")/.venv/bin/python}"
export MEDICAL_DATA_DIR="${MEDICAL_DATA_DIR:-/data/medical-web-v7/medical-web/data}"
export COOKIE_SECURE=1
cd "$project_dir"
exec bash run_devstream.sh
