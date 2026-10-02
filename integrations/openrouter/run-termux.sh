#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

if [[ "${PREFIX:-}" != *com.termux* ]]; then
  echo "Run this helper inside Termux on your Android phone." >&2
  exit 1
fi
if [[ ! -t 0 ]]; then
  echo "Use an interactive Termux session so you can press Enter after verification." >&2
  exit 1
fi

tasker_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
python_bin="$tasker_root/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then
  echo "Run bash integrations/openrouter/setup-termux.sh --visible first." >&2
  exit 1
fi
if ! command -v curl >/dev/null; then
  echo "Install curl with: pkg install curl" >&2
  exit 1
fi

export BWB_SERVER_DIR="${BWB_SERVER_DIR:-$HOME/.local/share/tasker/bwb-browser}"
export BWB_USER_DATA_DIR="${BWB_USER_DATA_DIR:-$HOME/.cache/tasker-bwb/x11-profile}"
export BWB_SCREENSHOTS_DIR="${BWB_SCREENSHOTS_DIR:-$HOME/.cache/tasker-bwb/screenshots}"
export BWB_ATTACH_PORT="${BWB_ATTACH_PORT:-9222}"
export BWB_HEADLESS=false
export BWB_FORCE_BROWSER=true
export BWB_LEAN=true
if [[ ! "$BWB_ATTACH_PORT" =~ ^[0-9]+$ || ${#BWB_ATTACH_PORT} -gt 5 ]]; then
  echo "BWB_ATTACH_PORT must be a port number from 1 to 65535." >&2
  exit 1
fi
BWB_ATTACH_PORT=$((10#$BWB_ATTACH_PORT))
if (( BWB_ATTACH_PORT < 1 || BWB_ATTACH_PORT > 65535 )); then
  echo "BWB_ATTACH_PORT must be a port number from 1 to 65535." >&2
  exit 1
fi
if ! curl -fsS --max-time 2 "http://127.0.0.1:$BWB_ATTACH_PORT/json/version" >/dev/null; then
  echo "No browser is ready on port $BWB_ATTACH_PORT." >&2
  echo "Run bash integrations/openrouter/start-x11-browser.sh first." >&2
  exit 1
fi

"$python_bin" "$tasker_root/integrations/openrouter/agent.py" --check-browser --timeout 60
if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  read -r -s -p "OpenRouter API key: " OPENROUTER_API_KEY
  printf '\n'
fi
export OPENROUTER_API_KEY
if [[ -z "${OPENROUTER_MODEL:-}" ]]; then
  read -r -p "Exact OpenRouter model ID supporting tool calls: " OPENROUTER_MODEL
fi
export OPENROUTER_MODEL

exec "$python_bin" -X utf8 "$tasker_root/integrations/openrouter/agent.py" \
  --url https://upfiles.com/mso6d --resume --pause-before-agent \
  --max-steps 25 --timeout 600 --verbose "$@"
