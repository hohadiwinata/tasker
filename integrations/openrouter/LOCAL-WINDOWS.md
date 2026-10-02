# Local Windows validation

Tested on this PC on 2 October 2026, using Python 3.13.0, Node 24.11.1,
installed Google Chrome, and bwb-browser v4.0.1 at commit
`ff8cd83eab7393d43777bebfd48276457ea5e045`.
The final interactive check used the local `bwb-force-browser.patch` described below.

The ZIP was extracted into `integrations/openrouter`. The dependency and isolated
browser profile are under `.local-test`, excluded from Git. No Python packages
were needed and the existing Tasker XML files were not changed.

## Results

- All 14 supplied tests passed, including real MCP discovery and the local
  static-page/mocked OpenRouter HTTP roundtrip.
- All upstream JavaScript modules passed Node syntax checks.
- MCP discovered 26 tools.
- Headless Chrome startup and CDP connection passed outside the Codex sandbox.
- The supplied version failed the additional interactive smoke test: static
  navigation returned page content without actually navigating Chrome. Subsequent
  clicks and page reads operated on the old page (or the new-tab page).
- With the local workaround enabled, `smoke-browser.py` passed real Chrome
  navigation, button clicking, resulting page text, title/URL, and the mocked HTTP
  agent loop. The mock supplies deterministic tool calls; model reasoning is not tested.
- Live OpenRouter requests were not tested: this session has no API key or model
  configured. No API credits were spent.
- Upfiles and Android/Termux were not tested.

The initial sandboxed browser launch returned `spawn EPERM`; it passed when
executed with permission to launch Chrome. Upstream emits `'ps' is not recognized`
warnings on Windows from Unix process-inspection/cleanup code. Browser operation
passed, but Windows memory accounting and orphan cleanup are not established.

`npm audit` reported four vulnerable dependency packages: `fast-uri` (high),
`hono`, `ip-address`, and `qs` (moderate). Exploitability in this stdio workflow
was not established. The pinned lockfile was retained for reproducible testing;
dependency remediation should be tested before considering this security-reviewed.

## Local navigation workaround

`bwb-force-browser.patch` adds an opt-in `BWB_FORCE_BROWSER=true` switch to the
pinned upstream server. Static-fetch results then proceed to real browser
navigation. `local-windows.ps1` enables it. This costs more browser resources;
without the variable, upstream's original static-first behavior is preserved.
The test dependency already has the patch applied. It does not change the Python
agent, Tasker XML exports, or original ZIP. It does not resolve npm vulnerabilities
or Unix process-inspection warnings.

## Repeat the checks

From the repository root in PowerShell:

```powershell
. ./integrations/openrouter/local-windows.ps1
python integrations/openrouter/agent.py --check --timeout 30
python integrations/openrouter/agent.py --check-browser --timeout 60
# The supplied integration test specifically expects static mode / no Chrome:
$env:BWB_FORCE_BROWSER = 'false'
python -m unittest discover -s integrations/openrouter -p 'test_*.py' -v
$env:BWB_FORCE_BROWSER = 'true'
python integrations/openrouter/smoke-browser.py
```

If browser detection fails, set the installed Chrome or Edge executable explicitly:

```powershell
$env:BWB_CHROME_PATH = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
```

The Termux installer and X11 helper are Android scripts; do not run them on Windows.

## Run with OpenRouter

### Pause for manual CAPTCHA verification

In the same PowerShell window where the API key and model are configured:

```powershell
. ./integrations/openrouter/local-windows.ps1
python -X utf8 integrations/openrouter/agent.py --url https://upfiles.com/mso6d --pause-before-agent --max-steps 25 --timeout 600 --verbose
```

`--pause-before-agent` opens visible Chrome and pauses immediately after opening
the start page, before any model request. Click Free Download yourself if needed,
complete verification, then press Enter in PowerShell. The current page is read
again and automation begins from your progress. This initial pause uses no tool
steps and also enables later manual CAPTCHA handoffs.

`--manual-captcha` alone opens visible Chrome and disables bwb's idle teardown for this
run. When the model observes a verification challenge, it can call the manual
handoff tool. The terminal pauses while you complete verification in Chrome.
Return to PowerShell and press Enter to resume, or type `q` and Enter to stop.
The agent then reads the current page and status in the same session without
returning to the starting URL. Human waiting time is excluded from `--timeout`;
the pause counts as one tool call. No OpenRouter requests occur during the pause.
The agent checks the new page rather than assuming verification succeeded.
Login, payment, installation, and permission decisions still stop the run.
The managed browser closes when the run finishes. This mode depends on the model
recognizing the challenge and requesting handoff; it does not automatically solve
or bypass CAPTCHA. If using `BWB_ATTACH_PORT`, supply an already-visible browser.

The Python client now passes `--headless false` explicitly to bwb for manual
modes: the pinned version's default config otherwise overrides the environment
setting. Each managed manual run uses a fresh `manual-profile-*` directory beside
the configured profile, avoiding reuse of an existing headless process. These
profiles remain on disk; they are not deleted automatically. Initial-pause mode
checks the browser connection before presenting the prompt and reports startup
errors instead of asking you to interact with a browser that failed to start.
Visible Chrome startup was verified using a Windows main-window handle and CDP.
The local smoke server ignores connection resets caused by browser shutdown;
other errors and test assertions remain visible.

The local fixture can test pause/resume without live CAPTCHA or API charges:

```powershell
python -X utf8 integrations/openrouter/smoke-browser.py --test-handoff
python -X utf8 integrations/openrouter/smoke-browser.py --test-start-pause
```

### Configure credentials

Configure the environment above, then enter credentials locally. The key prompt
is hidden and does not place the key itself in command history.

```powershell
$secret = Read-Host 'OpenRouter API key' -AsSecureString
$env:OPENROUTER_API_KEY = [System.Net.NetworkCredential]::new('', $secret).Password
Remove-Variable secret
$env:OPENROUTER_MODEL = Read-Host 'Exact OpenRouter model ID supporting tool calls'
python integrations/openrouter/agent.py --url https://example.com --goal 'Report the page title and URL.' --max-steps 5 --timeout 120
```

This uses a remote model through OpenRouter, incurs API charges, and sends page
observations to OpenRouter. The Python agent and browser run locally; inference
is not offline. Clear the key when finished:

```powershell
Remove-Item Env:OPENROUTER_API_KEY -ErrorAction SilentlyContinue
```

## Recreate the local dependency if missing

```powershell
git clone https://github.com/krshforever/bwb-browser.git .local-test/bwb-browser
git -C .local-test/bwb-browser checkout --detach ff8cd83eab7393d43777bebfd48276457ea5e045
git -C .local-test/bwb-browser apply ../../integrations/openrouter/bwb-force-browser.patch
Push-Location .local-test/bwb-browser
npm.cmd ci --ignore-scripts
Pop-Location
```

The Windows helper, patch, and browser smoke test were added locally and are not
included in the original ZIP.
