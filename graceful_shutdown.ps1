# Graceful shutdown script for LinkedIn Auto System
# This script sends Ctrl+C signals to the backend and frontend processes

Add-Type -TypeDefinition @'
    using System;
    using System.Runtime.InteropServices;
    public class Win32 {
        [DllImport("kernel32.dll")]
        public static extern bool GenerateConsoleCtrlEvent(uint dwCtrlEvent, uint dwProcessGroupId);
        [DllImport("kernel32.dll")]
        public static extern bool SetConsoleCtrlHandler(IntPtr handlerRoutine, bool add);
        [DllImport("kernel32.dll")]
        public static extern uint GetCurrentProcessId();
    }
'@

Write-Host "Looking for backend and frontend processes..."

# Show all Python processes for debugging
Write-Host "All Python processes:"
Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  PID: $($_.Id), Title: '$($_.MainWindowTitle)', Command: $($_.ProcessName)"
}

# Show all Node processes for debugging
Write-Host "All Node processes:"
Get-Process node -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  PID: $($_.Id), Title: '$($_.MainWindowTitle)', Command: $($_.ProcessName)"
}

# Show all CMD processes for debugging
Write-Host "All CMD processes:"
Get-Process cmd -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  PID: $($_.Id), Title: '$($_.MainWindowTitle)', Command: $($_.ProcessName)"
}

# Since window titles are empty, we'll target all Python and Node processes
# This is safe because we know these are the ones we started for our application
$backendProcesses = Get-Process python -ErrorAction SilentlyContinue
$frontendProcesses = Get-Process node -ErrorAction SilentlyContinue

# Also try to find CMD processes that might be hosting our applications
$cmdBackendProcesses = Get-Process cmd -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -like '*Backend*'}
$cmdFrontendProcesses = Get-Process cmd -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -like '*Frontend*'}

Write-Host "Found $($backendProcesses.Count) backend processes"
Write-Host "Found $($frontendProcesses.Count) frontend processes"
Write-Host "Found $($cmdBackendProcesses.Count) backend CMD processes"
Write-Host "Found $($cmdFrontendProcesses.Count) frontend CMD processes"

# Send Ctrl+C to backend processes
foreach ($process in $backendProcesses) {
    try {
        Write-Host "Sending Ctrl+C to backend process $($process.Id) (Title: '$($process.MainWindowTitle)')..."
        [Win32]::GenerateConsoleCtrlEvent(0, $process.Id)
        Start-Sleep -Milliseconds 500
    } catch {
        Write-Host "Failed to send Ctrl+C to backend process $($process.Id): $($_.Exception.Message)"
    }
}

# Send Ctrl+C to frontend processes
foreach ($process in $frontendProcesses) {
    try {
        Write-Host "Sending Ctrl+C to frontend process $($process.Id) (Title: '$($process.MainWindowTitle)')..."
        [Win32]::GenerateConsoleCtrlEvent(0, $process.Id)
        Start-Sleep -Milliseconds 500
    } catch {
        Write-Host "Failed to send Ctrl+C to frontend process $($process.Id): $($_.Exception.Message)"
    }
}

# Send Ctrl+C to CMD processes hosting our applications
foreach ($process in $cmdBackendProcesses) {
    try {
        Write-Host "Sending Ctrl+C to backend CMD process $($process.Id) (Title: '$($process.MainWindowTitle)')..."
        [Win32]::GenerateConsoleCtrlEvent(0, $process.Id)
        Start-Sleep -Milliseconds 500
    } catch {
        Write-Host "Failed to send Ctrl+C to backend CMD process $($process.Id): $($_.Exception.Message)"
    }
}

foreach ($process in $cmdFrontendProcesses) {
    try {
        Write-Host "Sending Ctrl+C to frontend CMD process $($process.Id) (Title: '$($process.MainWindowTitle)')..."
        [Win32]::GenerateConsoleCtrlEvent(0, $process.Id)
        Start-Sleep -Milliseconds 500
    } catch {
        Write-Host "Failed to send Ctrl+C to frontend CMD process $($process.Id): $($_.Exception.Message)"
    }
}

Write-Host "Graceful shutdown signals sent. Waiting 3 seconds..."
Start-Sleep -Seconds 3

# Force kill any remaining processes if needed
$remainingBackend = Get-Process python -ErrorAction SilentlyContinue
$remainingFrontend = Get-Process node -ErrorAction SilentlyContinue
$remainingCmdBackend = Get-Process cmd -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -like '*Backend*'}
$remainingCmdFrontend = Get-Process cmd -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -like '*Frontend*'}

if ($remainingBackend) {
    Write-Host "Force killing remaining backend processes..."
    $remainingBackend | Stop-Process -Force
}

if ($remainingFrontend) {
    Write-Host "Force killing remaining frontend processes..."
    $remainingFrontend | Stop-Process -Force
}

if ($remainingCmdBackend) {
    Write-Host "Force killing remaining backend CMD processes..."
    $remainingCmdBackend | Stop-Process -Force
}

if ($remainingCmdFrontend) {
    Write-Host "Force killing remaining frontend CMD processes..."
    $remainingCmdFrontend | Stop-Process -Force
}

Write-Host "Shutdown complete!"
