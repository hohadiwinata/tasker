#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

if [[ "${PREFIX:-}" != *com.termux* ]]; then
  echo "Run this script inside Termux on your Android phone." >&2
  exit 1
fi

visible=false
if [[ "${1:-}" == "--visible" && "$#" == 1 ]]; then
  visible=true
elif [[ "$#" != 0 ]]; then
  echo "Usage: bash setup-termux.sh [--visible]" >&2
  exit 1
fi

tasker_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
bwb_dir="${BWB_SERVER_DIR:-$HOME/.local/share/tasker/bwb-browser}"
bwb_commit="ff8cd83eab7393d43777bebfd48276457ea5e045" # Verified upstream v4.0.1.

pkg update
pkg install -y git nodejs-lts python python-pip
pkg install -y x11-repo
pkg install -y chromium
if [[ "$visible" == true ]]; then
  pkg install -y termux-x11-nightly xfce dbus curl
fi

if [[ ! -e "$bwb_dir" ]]; then
  mkdir -p -- "$(dirname -- "$bwb_dir")"
  git clone https://github.com/krshforever/bwb-browser.git "$bwb_dir"
  git -C "$bwb_dir" checkout --detach "$bwb_commit"
elif [[ ! -f "$bwb_dir/server.mjs" ]]; then
  echo "Existing path is not a bwb checkout: $bwb_dir" >&2
  exit 1
else
  echo "Using existing bwb checkout without changing its branch: $bwb_dir"
fi

navigation_patch="$tasker_root/integrations/openrouter/bwb-force-browser.patch"
if git -C "$bwb_dir" apply --reverse --check "$navigation_patch" 2>/dev/null; then
  echo "Browser navigation patch already applied."
elif git -C "$bwb_dir" apply --check "$navigation_patch"; then
  git -C "$bwb_dir" apply "$navigation_patch"
else
  echo "Navigation patch does not match this bwb checkout. Existing files were preserved." >&2
  exit 1
fi

(cd -- "$bwb_dir" && npm ci --ignore-scripts && npm test)
cd -- "$tasker_root"
python -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"'
if [[ ! -d .venv ]]; then
  python -m venv .venv
fi
mkdir -p -- "$HOME/.cache/tasker-bwb/profile" "$HOME/.cache/tasker-bwb/screenshots"
export BWB_SERVER_DIR="$bwb_dir"
export BWB_USER_DATA_DIR="$HOME/.cache/tasker-bwb/profile"
export BWB_SCREENSHOTS_DIR="$HOME/.cache/tasker-bwb/screenshots"
export BWB_HEADLESS=true
export BWB_LEAN=true
# Clear an old attach setting for the managed headless installation check.
unset BWB_ATTACH_PORT
.venv/bin/python integrations/openrouter/agent.py --check
.venv/bin/python integrations/openrouter/agent.py --check-browser --timeout 60
echo "Setup complete. Follow integrations/openrouter/README.md to configure OpenRouter."
if [[ "$visible" == true ]]; then
  echo "Install the Termux:X11 Android APK, then follow TERMUX-MANUAL.md."
fi
