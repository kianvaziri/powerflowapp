#!/usr/bin/env bash
set -euo pipefail

if [ -x ".venv/bin/python" ]; then
  .venv/bin/python -m src.validation.run_m5_fault_demo "$@"
else
  python3 -m src.validation.run_m5_fault_demo "$@"
fi
