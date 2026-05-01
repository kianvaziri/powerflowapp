#!/bin/zsh

# Double-click launcher for the EE4310 Power Flow UI (macOS)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Ensure local imports resolve correctly.
export PYTHONPATH="$SCRIPT_DIR"

# Ensure virtual environment exists.
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv || {
    echo "Failed to create .venv"
    read -r "?Press Enter to close..."
    exit 1
  }
fi

# Install/update dependencies.
echo "Installing dependencies (if needed)..."
.venv/bin/python -m pip install -r requirements.txt || {
  echo "Dependency installation failed"
  read -r "?Press Enter to close..."
  exit 1
}

# Launch Streamlit UI.
echo "Starting Power Flow UI..."
echo "If browser does not open automatically, go to: http://localhost:8501"
.venv/bin/streamlit run src/ui/streamlit_app.py

# Keep terminal window open if Streamlit exits unexpectedly.
echo "UI stopped."
read -r "?Press Enter to close..."
