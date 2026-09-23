#!/usr/bin/env bash
# Idempotent Cloud Agent setup for the Streamlit product-data-consolidation app.
set -euo pipefail

cd "$(dirname "$0")/.."

# The default image ships Python 3.12 but not the venv/pip modules; add them if missing.
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3-venv python3-pip
fi

# Create the virtual environment only when it does not already exist.
if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
. .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

echo "Environment setup complete."
