#!/bin/zsh
set -eu
cd -- "${0:A:h}"
PV_ENV="${TMPDIR:-/tmp}/haus-pv-board-runtime"
if [[ -x /tmp/haus-pv-board-venv/bin/python ]]; then
  PV_ENV=/tmp/haus-pv-board-venv
fi
if [[ ! -x "$PV_ENV/bin/python" ]]; then
  python3 -m venv "$PV_ENV"
fi
if ! "$PV_ENV/bin/python" -c 'import streamlit; assert streamlit.__version__ == "1.67.0"' 2>/dev/null; then
  "$PV_ENV/bin/python" -m pip install -r requirements.txt
fi
exec "$PV_ENV/bin/python" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
