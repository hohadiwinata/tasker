#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

if [[ "${PREFIX:-}" != *com.termux* ]]; then
  echo "Run this script inside Termux." >&2
  exit 1
fi

for required in termux-x11 chromium dbus-launch curl; do
  if ! command -v "$required" >/dev/null; then
    echo "Missing $required. Install the Termux:X11 APK, then run:" >&2
    echo "pkg install x11-repo && pkg install termux-x11-nightly xfce chromium dbus curl" >&2
    exit 1
  fi
done

x11_display="${TASKER_X11_DISPLAY:-:1}"
browser_profile="$HOME/.cache/tasker-bwb/x11-profile"
log_dir="$HOME/.cache/tasker-bwb"
mkdir -p -- "$browser_profile" "$log_dir"

if curl -fsS --max-time 2 http://127.0.0.1:9222/json/version >/dev/null 2>&1; then
  echo "CDP port 9222 is already in use. No browser was launched or attached." >&2
  echo "Use your existing browser explicitly or close it before running this script." >&2
  exit 1
fi

# These graphical processes do not need the exported API credential.
env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL \
  termux-x11 "$x11_display" \
  -xstartup "dbus-launch --exit-with-session xfce4-session" \
  >"$log_dir/x11.log" 2>&1 &

echo "Open the Termux:X11 Android app and wait for the desktop."
read -r -p "When the desktop appears, press Enter here to launch Chromium: "

env -u OPENROUTER_API_KEY -u OPENROUTER_MODEL DISPLAY="$x11_display" \
  dbus-launch --exit-with-session chromium \
  --ozone-platform=x11 --no-sandbox --disable-gpu --disable-dev-shm-usage \
  --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 \
  --user-data-dir="$browser_profile" \
  https://upfiles.com/mso6d >"$log_dir/x11-chromium.log" 2>&1 &

browser_ready=false
for attempt in {1..30}; do
  if curl -fsS --max-time 1 http://127.0.0.1:9222/json/version >/dev/null 2>&1; then
    browser_ready=true
    break
  fi
  sleep 1
done

if [[ "$browser_ready" != true ]]; then
  echo "Chromium's debugging endpoint did not become ready." >&2
  echo "Read $log_dir/x11-chromium.log and $log_dir/x11.log for errors." >&2
  exit 1
fi

echo "Visible Chromium is ready. In this Termux shell, run:"
echo "export BWB_ATTACH_PORT=9222"
echo "export BWB_HEADLESS=false"
echo "Then run: bash integrations/openrouter/run-termux.sh"
echo "The browser remains open after the agent exits; close its window when finished."
