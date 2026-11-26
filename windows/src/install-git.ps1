# Fetches the newest Git for Windows installer from its releases on GitHub and runs it without its windows.
$ErrorActionPreference = 'Stop'
# The progress bar makes a download many times slower, and nobody sees it here.
$ProgressPreference = 'SilentlyContinue'

$release = Invoke-RestMethod 'https://api.github.com/repos/git-for-windows/git/releases/latest'
$asset = $release.assets | Where-Object { $_.name -match '^Git-[\d.]+-64-bit\.exe$' } | Select-Object -First 1
if (-not $asset) { throw 'The newest Git for Windows release has no 64-bit installer.' }

$installer = Join-Path $env:TEMP $asset.name
Invoke-WebRequest $asset.browser_download_url -OutFile $installer
$ran = Start-Process $installer -ArgumentList '/VERYSILENT', '/NORESTART', '/NOCANCEL', '/SP-' -Wait -PassThru
Remove-Item $installer
if ($ran.ExitCode -ne 0) { throw ('The Git for Windows installer ended with code {0}.' -f $ran.ExitCode) }
