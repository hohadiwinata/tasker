# Android: visible browser and manual CAPTCHA handoff

Use the updated `tasker-openrouter-termux.zip`; the original ZIP lacks the fixes
and new helper. This package contains only the OpenRouter integration, not your
Tasker configuration or credentials. No Git push or publication is required.

## 1. Install the Android apps

Keep your existing Termux installation. If installing for the first time, use
the official Termux F-Droid or GitHub distribution:
https://github.com/termux/termux-app#installation

Install `termux-x11-universal-debug.apk` from the official Termux:X11 nightly
release: https://github.com/termux/termux-x11/releases/tag/nightly

Termux:X11 needs both this Android app and its companion package, which the
installer below supplies. Android 8 or later is required. The regular universal
APK avoids the sharedUid variant's Termux-signature requirements. Instructions:
https://github.com/termux/termux-x11#setup-instructions

## 2. Copy the package and install

Copy `tasker-openrouter-termux.zip` from your PC to your phone's Download folder.
Then run these commands in Termux. Grant the storage prompt when requested:

```bash
termux-setup-storage
pkg update
pkg install unzip
mkdir -p ~/tasker-openrouter-phone
unzip -n ~/storage/downloads/tasker-openrouter-termux.zip -d ~/tasker-openrouter-phone
cd ~/tasker-openrouter-phone
bash integrations/openrouter/setup-termux.sh --visible
```

Use this as a new install directory. If it already contains a previous integration,
choose another new directory instead: `unzip -n` deliberately preserves existing
files. Run from Termux home, not Android shared storage.

Setup installs Python, Node, Chromium, Termux:X11's companion, XFCE, D-Bus and curl.
It creates `.venv`, installs the pinned bwb dependency, applies the opt-in real
browser navigation patch, and checks MCP plus headless Chromium/CDP. It preserves
an existing bwb checkout's branch and fails if the patch cannot apply cleanly.
The pinned dependencies previously reported four npm advisories; this package
does not remediate them. The Python agent requires no additional pip packages.

## 3. Start the visible browser

```bash
cd ~/tasker-openrouter-phone
bash integrations/openrouter/start-x11-browser.sh
```

At the prompt, switch to the Termux:X11 Android app and wait for the desktop.
Return to Termux and press Enter. Switch back to Termux:X11 to see Chromium.
The helper opens Upfiles with a dedicated profile and CDP on loopback port 9222.
If port 9222 is already in use, it stops rather than silently taking over a session.
It does not start the model or send any OpenRouter requests.

## 4. Start the agent and verify manually

Return to Termux:

```bash
cd ~/tasker-openrouter-phone
bash integrations/openrouter/run-termux.sh
```

The helper verifies the browser connection first. It asks for your OpenRouter key
with hidden input and your exact model ID if they are not already exported. Use a
model supporting tool calls. Credentials are not stored in files or shell history;
do not enable shell tracing. Model requests cost API credits and send page
observations to OpenRouter. The model runs remotely.

The terminal then pauses **before the first model request**:

1. Switch to Termux:X11 and click **Free Download**.
2. Close the extra ad window, keeping the original Upfiles window open.
3. Complete the CAPTCHA yourself. Wait until Continue becomes enabled.
4. Switch back to Termux and press **Enter**.

The agent rereads the same browser session and continues from your progress.
It can pause again if the model recognizes another CAPTCHA. Type `q` and Enter
at a pause, or Ctrl+C during a run, to stop. Human waiting time is excluded from
the 600-second agent timeout. No API calls occur while paused. Other decisions
such as login, payment, installing software, and browser permissions remain blockers.

The browser stays open after the agent exits because it is attached to the
separately started Chromium. Close its window yourself when finished. Keep tabs
few: bwb does not enforce its automatic browser memory guard in attach mode,
and Android can stop processes when memory/background limits are reached.

To retry from the current page, rerun `run-termux.sh`; it uses `--resume` and does
not reset the page to the original URL. Optional overrides are passed through:

```bash
bash integrations/openrouter/run-termux.sh --max-steps 10 --timeout 300
```

## Troubleshooting

- No desktop: check `~/.cache/tasker-bwb/x11.log`. Some devices need Termux:X11's
  `-legacy-drawing` option; stop the old X11 session before changing it.
- No browser: check `~/.cache/tasker-bwb/x11-chromium.log` and `chromium --version`.
- Browser closed or Termux killed: allow unrestricted battery usage if available.
  `termux-wake-lock` can help keep the CPU awake; use `termux-wake-unlock` afterward.
  A wake lock does not prevent memory kills.
- CAPTCHA missing or not loading: check the visible browser; there is no automated
  CAPTCHA solver or site-check bypass in this package.
- APK selection and X11 package versions: use the official Termux:X11 instructions
  above and current repository packages.

The Python tests, real Chrome handoff, and visible window were verified on Windows.
Android package installation, touch interaction, memory behavior, and the live
Upfiles flow require testing on your phone. Phone operation is not yet verified.
