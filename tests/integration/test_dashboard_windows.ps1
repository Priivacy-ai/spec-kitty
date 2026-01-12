# Test Dashboard on Windows
# Validates fix for ERR_EMPTY_RESPONSE issue

Write-Host "==================================="
Write-Host "Windows Dashboard Integration Test"
Write-Host "==================================="

$TestDir = "$env:TEMP\test-dashboard-windows"
if (Test-Path $TestDir) {
    Remove-Item -Recurse -Force $TestDir
}
New-Item -ItemType Directory -Path $TestDir | Out-Null
Set-Location $TestDir

Write-Host ""
Write-Host "Step 1: Creating test project..."
git init

# Initialize spec-kitty project (interactive)
spec-kitty init

# Create dummy feature for dashboard
New-Item -ItemType Directory -Path "kitty-specs\001-test-feature" -Force | Out-Null
@"
# Test Feature Spec
## User Scenarios
Test feature for dashboard validation.
"@ | Out-File -FilePath "kitty-specs\001-test-feature\spec.md" -Encoding UTF8

Write-Host ""
Write-Host "Step 2: Starting dashboard..."
Start-Process -FilePath "spec-kitty" -ArgumentList "dashboard" -NoNewWindow -PassThru | Out-Null
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Step 3: Verifying dashboard process..."
$DashboardProc = Get-Process | Where-Object { $_.ProcessName -like "*python*" -and $_.CommandLine -like "*dashboard*" }
if ($null -eq $DashboardProc) {
    Write-Host "✗ Dashboard process not found!"
    exit 1
}
Write-Host "✓ Dashboard process running (PID: $($DashboardProc.Id))"

Write-Host ""
Write-Host "Step 4: Testing HTTP response..."
try {
    $Response = Invoke-WebRequest -Uri "http://127.0.0.1:9237" -UseBasicParsing -TimeoutSec 5

    if ($Response.StatusCode -ne 200) {
        Write-Host "✗ HTTP error: $($Response.StatusCode)"
        exit 1
    }

    if ($Response.Content.Length -le 0) {
        Write-Host "✗ Empty response (ERR_EMPTY_RESPONSE)"
        exit 1
    }

    if ($Response.Content -match "<html") {
        Write-Host "✓ Response contains HTML"
    } else {
        Write-Host "⚠ Response doesn't look like HTML"
    }

} catch {
    Write-Host "✗ HTTP request failed: $_"
    exit 1
}

Write-Host ""
Write-Host "Step 5: Stopping dashboard..."
spec-kitty dashboard --stop

Write-Host "✓ Dashboard stopped"
Write-Host "PASS: Windows dashboard test completed"
