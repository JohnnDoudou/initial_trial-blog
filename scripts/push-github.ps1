# Push to GitHub via local v2rayN SOCKS proxy.
# Token is stored locally in .secrets/github_token (gitignored) so you reuse it.
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\push-github.ps1
#   or double-click 推送到GitHub.bat

$ErrorActionPreference = "Stop"
$env:Path = "C:\Program Files\Git\cmd;" + $env:Path

$env:ALL_PROXY = "socks5h://127.0.0.1:10808"
$env:HTTPS_PROXY = "socks5h://127.0.0.1:10808"
$env:HTTP_PROXY = "socks5h://127.0.0.1:10808"

Set-Location $PSScriptRoot\..
$repoRoot = (Get-Location).Path
$secretDir = Join-Path $repoRoot ".secrets"
$tokenFile = Join-Path $secretDir "github_token"

function Read-Token {
    if (Test-Path $tokenFile) {
        $saved = (Get-Content -Path $tokenFile -Raw -Encoding utf8).Trim()
        if (-not [string]::IsNullOrWhiteSpace($saved)) {
            Write-Host "Using saved token from .secrets\github_token"
            return $saved
        }
    }

    Write-Host ""
    Write-Host "No saved token yet. Paste your GitHub token, then press Enter."
    Write-Host "Prompt is only the word Token - do NOT put the token inside quotes."
    Write-Host "It will be saved locally for next time (file is gitignored)."
    Write-Host ""
    $inputToken = Read-Host "Token"
    if ([string]::IsNullOrWhiteSpace($inputToken)) {
        throw "Token is empty."
    }
    $inputToken = $inputToken.Trim()
    New-Item -ItemType Directory -Force -Path $secretDir | Out-Null
    Set-Content -Path $tokenFile -Value $inputToken -Encoding utf8 -NoNewline
    Write-Host "Token saved to .secrets\github_token"
    return $inputToken
}

$token = Read-Token
$escaped = [uri]::EscapeDataString($token)
$remote = "https://x-access-token:$escaped@github.com/JohnnDoudou/initial_trial-blog.git"

Write-Host "Local commits:"
git log --oneline origin/main..HEAD 2>$null
Write-Host "Pushing main..."
try {
    git -c credential.helper= push -u $remote main
} catch {
    Write-Host ""
    Write-Host "Push failed. If GitHub says bad credentials, delete .secrets\github_token and run again with a new token."
    throw
}

# Never leave the token inside remote/upstream URLs.
git remote set-url origin "https://github.com/JohnnDoudou/initial_trial-blog.git"
git branch --set-upstream-to=origin/main main 2>$null
Write-Host "Done. Remote URL cleaned (token not stored in git remote)."
Write-Host "Check Actions: https://github.com/JohnnDoudou/initial_trial-blog/actions"
Write-Host "Site (after green deploy): https://JohnnDoudou.github.io/initial_trial-blog/"
