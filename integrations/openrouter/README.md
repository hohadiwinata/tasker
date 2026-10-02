# Termux Python agent with OpenRouter and bwb

For the updated Android manual-verification workflow, start with
[TERMUX-MANUAL.md](TERMUX-MANUAL.md) and `tasker-openrouter-termux.zip`.

This repository holds the Python agent. The browser tools come from the separate
[bwb-browser repository](https://github.com/krshforever/bwb-browser). The agent
starts bwb's `node server.mjs` as a child process and communicates over local
stdio. There is no MCP HTTP port to expose or a server to start in another tab.

Python 3.11+, Node 18+, and Termux Chromium are required. The client uses only
Python's standard library: no Python MCP SDK, Rust build, or pip install is needed.
The installer pins a new bwb checkout to verified upstream v4.0.1. An existing
checkout at `BWB_SERVER_DIR` is used without changing its branch.

## Install on your Android phone

Use a current [Termux F-Droid build](https://f-droid.org/packages/com.termux/) or
[official GitHub build](https://github.com/termux/termux-app/releases). Termux
plugins must come from the same source as the app. If Termux is already installed,
keep it and try the commands below; do not uninstall it and lose existing files.

Run these commands in Termux, one at a time. Keep the project in Termux's home
directory rather than Android shared storage, which has execution/symlink limits.

```bash
pkg update
pkg upgrade
pkg install git
cd ~
git clone https://github.com/hohadiwinata/tasker.git
cd ~/tasker
bash integrations/openrouter/setup-termux.sh
```

These last two commands require a revision containing this integration. If using
the supplied ZIP before the changes are published, save `tasker-openrouter.zip` in
your phone's Download folder. After cloning the repository, use:

```bash
termux-setup-storage
pkg install unzip
cd ~/tasker
unzip -n ~/storage/downloads/tasker-openrouter.zip
bash integrations/openrouter/setup-termux.sh
```

Android will ask to grant Termux storage access for reading the ZIP. This is not
needed when obtaining the integration from Git. `unzip -n` preserves any existing
files; for a later update, review the changed files before replacing them.

The installer enables `x11-repo`, installs Chromium, runs bwb's syntax checks,
creates `.venv`, and performs two checks: MCP tool discovery and Chromium/CDP
startup. Headless Chromium does not need a display app. The phone's ordinary
Chrome Android app cannot substitute for the Termux Chromium executable.

## Configure and run

In each new Termux shell:

```bash
cd ~/tasker
source .venv/bin/activate
export BWB_SERVER_DIR="$HOME/.local/share/tasker/bwb-browser"
export BWB_USER_DATA_DIR="$HOME/.cache/tasker-bwb/profile"
export BWB_SCREENSHOTS_DIR="$HOME/.cache/tasker-bwb/screenshots"
export BWB_HEADLESS=true
export BWB_LEAN=true
```

Create an API key in [OpenRouter](https://openrouter.ai/settings/keys). Enter it
at the hidden prompt below, so the key itself is not a shell history command.
Do not send it in chat, save it to Git, or enable shell tracing (`set -x`).

```bash
read -r -s -p 'OpenRouter API key: ' OPENROUTER_API_KEY
printf '\n'
export OPENROUTER_API_KEY
read -r -p 'Exact OpenRouter model ID: ' OPENROUTER_MODEL
export OPENROUTER_MODEL
```

Choose a current model on [OpenRouter's models page](https://openrouter.ai/models)
that supports tool calling, and copy its exact `provider/model` ID. An internal
Codex model label is not an OpenRouter model ID. API usage incurs costs.

First test a simple page:

```bash
python integrations/openrouter/agent.py \
  --url https://example.com \
  --goal 'Report the page title and URL.' \
  --max-steps 5 --timeout 120
```

Then run the gate task from your guide:

```bash
python integrations/openrouter/agent.py \
  --url https://upfiles.com/mso6d \
  --max-steps 25 --timeout 600
```

The default goal follows the gate's visible flow and reports the destination or
a blocker. `--goal` can describe the expected destination/content. Initial
navigation is outside the tool-call budget; each requested tool call, including
local countdown waits and rejected calls, uses one step. Each API response is
capped at 1,500 generated tokens. Model history accumulates during a run, so input
token costs can grow even though each observation is capped at 12,000 characters.
Ctrl+C stops the client and its MCP child. The API key is filtered out of the
child environment before bwb starts.

The offered tools navigate, read, click, wait, inspect status, and switch existing
tabs. JavaScript evaluation, fingerprint changes, downloads, installs, filling
forms, and loading saved cookies are not exposed. The agent is instructed to stop
for CAPTCHA, login, payment, installation, or permission decisions. These are
model instructions, not a security sandbox. Browser redirects can leave the
starting domain, and observed page text is sent to OpenRouter. Use the separate
browser profile above. Headless mode does not provide a visible browser window;
`BWB_HEADLESS=false` also requires a display setup such as Termux:X11.

## Visible Chromium with Termux:X11

Termux:X11 needs both its Android APK and a Termux companion package. Install
`termux-x11-universal-debug.apk` from the official
[nightly release](https://github.com/termux/termux-x11/releases/tag/nightly).
Use the regular APK; the sharedUid variant has additional Termux-signature
requirements. See the [official instructions](https://github.com/termux/termux-x11#setup-instructions).

In Termux:

```bash
pkg update
pkg install x11-repo
pkg install termux-x11-nightly xfce chromium dbus curl
cd ~/tasker
bash integrations/openrouter/start-x11-browser.sh
```

The helper starts the X11 desktop. Open the Termux:X11 Android app, wait for
the desktop, then return to Termux and press Enter at the prompt. Chromium
opens Upfiles with a separate profile and a debugging endpoint on loopback
port 9222. A pre-existing listener on that port is reported rather than reused
automatically. The helper removes the OpenRouter key/model from the graphical
processes' environment. It does not start the Python agent or make API calls.

Return to the same Termux shell, where your API key and model remain exported:

```bash
source .venv/bin/activate
export BWB_ATTACH_PORT=9222
export BWB_HEADLESS=false
python integrations/openrouter/agent.py --check-browser --timeout 60
python integrations/openrouter/agent.py --url https://upfiles.com/mso6d \
  --resume --pause-before-agent --max-steps 25 --timeout 600 --verbose
```

`--resume` reads the current attached page instead of initially navigating back
to `--url`. The original URL remains context for the goal. Initial page/status
inspection is outside the tool-call budget. The agent can still navigate if
needed to complete the goal. If it stops for a decision, inspect the page in
Termux:X11, make any required decision yourself, then run `--resume` again.
The helper does not supply a way to solve CAPTCHA or override site checks.
A visible browser may still show the same adblock message.

In attach mode bwb disconnects when the agent ends and leaves Chromium open.
It does not apply its automatic memory shedding to an attached browser, and
its resource readings do not measure the foreign browser's process tree.
Keep tabs few and close Chromium's window when done. To return to managed
headless sessions:

```bash
unset BWB_ATTACH_PORT
export BWB_HEADLESS=true
```

If the X11 desktop is blank, check `~/.cache/tasker-bwb/x11.log`. The official
instructions suggest `-legacy-drawing` for some devices; stop your X11 server
before restarting it with different options. If Chromium fails, check
`~/.cache/tasker-bwb/x11-chromium.log`. Rerunning the helper can encounter an
already-running X11 server; it does not kill existing sessions.

## Checks and troubleshooting

```bash
python integrations/openrouter/agent.py --check
python integrations/openrouter/agent.py --check-browser --timeout 60
BWB_TEST_SERVER_DIR="$BWB_SERVER_DIR" \
  python -m unittest discover -s integrations/openrouter -p 'test_*.py'
```

`--check` needs no API key and does not start Chromium. `--check-browser` starts
Chromium/CDP using the configured profile and makes no OpenRouter requests. It
can restore earlier tabs in that profile. The optional integration test uses a
local page and a mock OpenRouter HTTP endpoint; no API credits are spent.

- `server.mjs` not found: check `BWB_SERVER_DIR` or pass `--server-dir /absolute/path/to/bwb-browser`.
- Package repository errors: run `termux-change-repo`, select a working mirror, and retry `pkg update`.
- Chromium package unavailable: ensure `pkg install x11-repo` succeeded; package availability depends on phone architecture and mirror.
- Chromium startup failure: run `chromium --version` and share the error from `--check-browser`.
- HTTP 401/402: check your OpenRouter key/credits. Model or tool errors: check the exact model ID and its tool support.
- `[Process completed (signal 9)]`: Android may have stopped Termux/Chromium for memory or background limits. Set Termux battery usage to Unrestricted if available, keep tabs few, and use `termux-wake-lock` during a session. Run `termux-wake-unlock` afterward. Wake locks do not prevent memory kills.

### Browser stopped by bwb's memory guard

If a run reports repeated memory stops, retry with `--verbose`. This prints bwb's
resource footers directly to the terminal, including peak readings and
`oom-guard` actions, without printing the API key or page observations.

```bash
export BWB_LEAN=true
export BWB_TAB_MAX=1
python integrations/openrouter/agent.py --url https://upfiles.com/mso6d \
  --max-steps 5 --timeout 120 --verbose
```

Lean mode's default warning/critical thresholds are 300/450 MB for combined MCP
and Chromium RSS. A JavaScript-heavy page can exceed 450 MB even when the phone
has free RAM. RSS is a process-tree estimate and can count shared memory more
than once; it is not the same as unique physical memory use. The guard stops
Chromium independently of Android's own process limits. Increasing steps or the
agent deadline does not change these thresholds.

Check phone memory without displaying any credentials:

```bash
python - <<'PY'
from pathlib import Path
for line in Path('/proc/meminfo').read_text().splitlines():
    if line.startswith(('MemTotal:', 'MemAvailable:')):
        name, value, _ = line.split()
        print(name, round(int(value) / 1024), 'MiB')
PY
```

Choose any threshold increase from the observed peak and available RAM, rather
than disabling the guard. `BWB_WARN_MB` and `BWB_CRIT_MB` override the defaults
for the next MCP child; changing them cannot prevent an Android memory kill.
`BWB_NUCLEAR=true` also enables single-process Chromium to reduce memory, but it
can be less stable; use it only as an explicit troubleshooting experiment and
`unset BWB_NUCLEAR` afterward.

Validation in the development workspace covers the real bwb stdio handshake,
tool schemas, a local static page, and a mocked HTTP tool roundtrip. Live
OpenRouter, the Upfiles gate, Chromium startup, and Android 17 behavior require
verification on your phone. A successful gate result is not guaranteed.
