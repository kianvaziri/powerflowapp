#!/usr/bin/env bash
set -euo pipefail

if [ -x ".venv/bin/streamlit" ]; then
  .venv/bin/streamlit run src/ui/streamlit_app.py
else
  streamlit run src/ui/streamlit_app.py
fi
