# Dot-source this file from PowerShell to configure the current shell.
$taskerRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$bwbPath = Join-Path $taskerRoot '.local-test/bwb-browser'
if (-not (Test-Path -LiteralPath (Join-Path $bwbPath 'server.mjs'))) {
    throw 'Local bwb checkout is missing. See LOCAL-WINDOWS.md for setup.'
}
if (-not (Select-String -LiteralPath (Join-Path $bwbPath 'server.mjs') -Pattern 'BWB_FORCE_BROWSER' -Quiet)) {
    throw 'Apply integrations/openrouter/bwb-force-browser.patch as described in LOCAL-WINDOWS.md first.'
}
$env:BWB_SERVER_DIR = $bwbPath
$env:BWB_TEST_SERVER_DIR = $bwbPath
$env:BWB_USER_DATA_DIR = Join-Path $taskerRoot '.local-test/profile'
$env:BWB_SCREENSHOTS_DIR = Join-Path $taskerRoot '.local-test/screenshots'
$env:BWB_HEADLESS = 'true'
$env:BWB_FORCE_BROWSER = 'true'
Remove-Item Env:BWB_ATTACH_PORT -ErrorAction SilentlyContinue
Write-Host 'Local bwb environment configured with a separate headless browser profile.'
