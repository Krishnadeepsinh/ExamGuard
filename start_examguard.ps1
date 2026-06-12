$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontend = Join-Path $root "frontend"

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Installing frontend dependencies..."
    Push-Location $frontend
    npm install
    Pop-Location
}

$backendListening = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if (-not $backendListening) {
    Start-Process -FilePath python -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $root -WindowStyle Hidden
}

$frontendListening = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if (-not $frontendListening) {
    Start-Process -FilePath npm.cmd -ArgumentList "run", "dev", "--", "--host", "127.0.0.1" -WorkingDirectory $frontend -WindowStyle Hidden
}

Start-Sleep -Seconds 3

try {
    $health = Invoke-RestMethod "http://127.0.0.1:8000/health"
    Write-Host "Backend: ready ($($health.store) store, $($health.agents) agents)"
} catch {
    Write-Error "Backend did not start. Run: python -m uvicorn backend.main:app --reload"
}

Write-Host "ExamGuard is ready: http://127.0.0.1:5173"
Start-Process "http://127.0.0.1:5173"
