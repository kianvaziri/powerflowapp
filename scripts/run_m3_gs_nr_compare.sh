#!/usr/bin/env bash
set -euo pipefail

if [ -x ".venv/bin/python" ]; then
  .venv/bin/python -m src.validation.run_m3_gs_nr_compare "$@"
else
  python3 -m src.validation.run_m3_gs_nr_compare "$@"
fi
