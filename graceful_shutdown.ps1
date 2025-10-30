# Graceful shutdown script for LinkedIn Auto System
# This script stops only the backend and frontend processes started by dashboard-windows.bat

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Shutting Down LinkedIn Auto System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to stop processes by window title
function Stop-ProcessByWindowTitle {
    param(
        [string]$Title,
        [string]$ProcessName
    )
    
    $found = $false
    Get-Process -Name $ProcessName -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_.MainWindowTitle -like "*$Title*") {
            Write-Host "Stopping $Title (PID: $($_.Id))..." -ForegroundColor Yellow
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
            $found = $true
        }
    }
    return $found
}

# Stop Backend (Python process running api_server.py)
Write-Host "[1/2] Stopping Backend Server..." -ForegroundColor Green
$backendStopped = Stop-ProcessByWindowTitle -Title "LinkedIn Backend" -ProcessName "python"
if (-not $backendStopped) {
    # Fallback: try to stop by port 5000
    $backendPID = (Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue).OwningProcess
    if ($backendPID) {
        Write-Host "Stopping backend on port 5000 (PID: $backendPID)..." -ForegroundColor Yellow
        Stop-Process -Id $backendPID -Force -ErrorAction SilentlyContinue
        $backendStopped = $true
    }
}

if ($backendStopped) {
    Write-Host "✓ Backend stopped" -ForegroundColor Green
} else {
    Write-Host "✗ Backend not found or already stopped" -ForegroundColor Gray
}

Start-Sleep -Seconds 1

# Stop Frontend (Node process running npm start)
Write-Host "[2/2] Stopping Frontend Server..." -ForegroundColor Green
$frontendStopped = Stop-ProcessByWindowTitle -Title "LinkedIn Frontend" -ProcessName "node"
if (-not $frontendStopped) {
    # Fallback: try to stop by port 3000
    $frontendPID = (Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue).OwningProcess
    if ($frontendPID) {
        Write-Host "Stopping frontend on port 3000 (PID: $frontendPID)..." -ForegroundColor Yellow
        Stop-Process -Id $frontendPID -Force -ErrorAction SilentlyContinue
        $frontendStopped = $true
    }
}

if ($frontendStopped) {
    Write-Host "✓ Frontend stopped" -ForegroundColor Green
} else {
    Write-Host "✗ Frontend not found or already stopped" -ForegroundColor Gray
}

# Also close the CMD windows if they're still open
Get-Process -Name "cmd" -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -like "*LinkedIn Backend*" -or $_.MainWindowTitle -like "*LinkedIn Frontend*"
} | ForEach-Object {
    Write-Host "Closing window: $($_.MainWindowTitle)..." -ForegroundColor Yellow
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 1

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Shutdown Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
