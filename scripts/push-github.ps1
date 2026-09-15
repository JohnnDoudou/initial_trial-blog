# One-shot push to GitHub via local v2rayN SOCKS proxy.
# Usage: right-click -> Run with PowerShell, or:
#   powershell -ExecutionPolicy Bypass -File .\scripts\push-github.ps1

$ErrorActionPreference = "Stop"
$env:Path = "C:\Program Files\Git\cmd;" + $env:Path

$env:ALL_PROXY = "socks5h://127.0.0.1:10808"
$env:HTTPS_PROXY = "socks5h://127.0.0.1:10808"
$env:HTTP_PROXY = "socks5h://127.0.0.1:10808"

Set-Location $PSScriptRoot\..

Write-Host ""
Write-Host "Paste your GitHub token, then press Enter."
Write-Host "(The prompt is only the word Token - do NOT put the token inside the quotes.)"
Write-Host ""
$token = Read-Host "Token"

if ([string]::IsNullOrWhiteSpace($token)) {
    throw "Token is empty. Run again and paste the token after the Token: prompt."
}

$token = $token.Trim()
$escaped = [uri]::EscapeDataString($token)
$remote = "https://x-access-token:$escaped@github.com/JohnnDoudou/initial_trial-blog.git"

Write-Host "Pushing main..."
git -c credential.helper= push -u $remote main

# Never leave the token inside remote/upstream URLs.
git remote set-url origin "https://github.com/JohnnDoudou/initial_trial-blog.git"
git branch --set-upstream-to=origin/main main 2>$null
Write-Host "Done. Remote URL cleaned (token removed from git config)."
