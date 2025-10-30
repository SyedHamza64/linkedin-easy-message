# Graceful shutdown script for LinkedIn Auto System
# This script stops only the backend and frontend processes started by dashboard-windows.bat

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Shutting Down LinkedIn Auto System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to kill process tree
function Stop-ProcessTree {
    param(
        [int]$ParentProcessId
    )
    
    # Get all child processes
    $children = Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $ParentProcessId }
    
    # Recursively kill children first
    foreach ($child in $children) {
        Stop-ProcessTree -ParentProcessId $child.ProcessId
    }
    
    # Kill the parent process
    try {
        Stop-Process -Id $ParentProcessId -Force -ErrorAction SilentlyContinue
    } catch {
        # Already stopped
    }
}

# Stop Backend (Python process running api_server.py)
Write-Host "[1/3] Stopping Backend Server..." -ForegroundColor Green
$backendStopped = $false

# Try to find backend by port 5000
$backendPID = (Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -First 1
if ($backendPID) {
    Write-Host "Found backend on port 5000 (PID: $backendPID)" -ForegroundColor Yellow
    Stop-ProcessTree -ParentProcessId $backendPID
    $backendStopped = $true
}

# Also try to find by window title
Get-Process -Name "python" -ErrorAction SilentlyContinue | ForEach-Object {
    $cmdline = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    if ($cmdline -like "*api_server.py*") {
        Write-Host "Found backend process (PID: $($_.Id))" -ForegroundColor Yellow
        Stop-ProcessTree -ParentProcessId $_.Id
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
Write-Host "[2/3] Stopping Frontend Server..." -ForegroundColor Green
$frontendStopped = $false

# Try to find frontend by port 3000
$frontendPID = (Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -First 1
if ($frontendPID) {
    Write-Host "Found frontend on port 3000 (PID: $frontendPID)" -ForegroundColor Yellow
    Stop-ProcessTree -ParentProcessId $frontendPID
    $frontendStopped = $true
}

# Kill all node processes related to our app (more aggressive approach)
Get-Process -Name "node" -ErrorAction SilentlyContinue | ForEach-Object {
    $cmdline = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
    if ($cmdline -like "*linkedin-frontend*" -or $cmdline -like "*react-scripts*") {
        Write-Host "Found frontend process (PID: $($_.Id))" -ForegroundColor Yellow
        Stop-ProcessTree -ParentProcessId $_.Id
        $frontendStopped = $true
    }
}

if ($frontendStopped) {
    Write-Host "✓ Frontend stopped" -ForegroundColor Green
} else {
    Write-Host "✗ Frontend not found or already stopped" -ForegroundColor Gray
}

Start-Sleep -Seconds 1

# Close the CMD windows
Write-Host "[3/3] Closing launcher windows..." -ForegroundColor Green
Get-Process -Name "cmd" -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -like "*LinkedIn Backend*" -or $_.MainWindowTitle -like "*LinkedIn Frontend*"
} | ForEach-Object {
    Write-Host "Closing window: $($_.MainWindowTitle)..." -ForegroundColor Yellow
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Shutdown Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
