param(
    [string]$ArchivePath = 'C:\server01\_backend-deploy.zip'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$serverRoot = 'C:\server01'
$taskName = 'MoaBackendApi'
$stagingPath = Join-Path $serverRoot '_backend-stage'
$liveAppPath = Join-Path $serverRoot 'app'
$requirementsPath = Join-Path $serverRoot 'requirements.txt'
$venvsPath = Join-Path $serverRoot 'venvs'
$deploymentVenvPath = Join-Path $venvsPath "deploy-$([guid]::NewGuid().ToString('N'))"
$deploymentPython = Join-Path $deploymentVenvPath 'Scripts\python.exe'
$appBackupPath = Join-Path $serverRoot '_app-previous'
$requirementsBackupPath = Join-Path $serverRoot '_requirements-previous.txt'
$previousPython = $null
$newAppInstalled = $false
$deploymentCommitted = $false
$deploymentTaskMayUseVenv = $false

function Stop-BackendTask {
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if (-not $task -or $task.State -ne 'Running') {
        return
    }

    Stop-ScheduledTask -TaskName $taskName
    $deadline = (Get-Date).AddSeconds(20)
    do {
        Start-Sleep -Seconds 1
        $task = Get-ScheduledTask -TaskName $taskName
        if ($task.State -ne 'Running') {
            return
        }
    } while ((Get-Date) -lt $deadline)

    throw "Scheduled task '$taskName' did not stop."
}

function Get-BackendListenerProcessIds {
    if (-not (Get-Command 'Get-NetTCPConnection' -ErrorAction SilentlyContinue)) {
        throw 'The Windows NetTCPIP module is required to inspect port 8000 ownership.'
    }

    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction Stop)
    return @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
}

function Assert-BackendListenerManaged {
    param($Task)

    $listenerProcessIds = @(Get-BackendListenerProcessIds)
    if ($listenerProcessIds.Count -eq 0) {
        return
    }
    if (-not $Task -or $Task.State -ne 'Running') {
        throw 'Port 8000 is already in use outside the running MoaBackendApi task. Stop the existing backend process or supervisor before its first managed deployment.'
    }

    $expectedPython = [IO.Path]::GetFullPath($Task.Actions[0].Execute)
    foreach ($processId in $listenerProcessIds) {
        $process = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
        if (-not $process -or [string]::IsNullOrWhiteSpace($process.ExecutablePath) -or
            [IO.Path]::GetFullPath($process.ExecutablePath) -ne $expectedPython -or
            $process.CommandLine -notmatch '(?i)-m\s+uvicorn\s+app\.main:app') {
            throw "Port 8000 has a listener that does not match the running MoaBackendApi task (PID $processId). Stop or migrate that process before deploying."
        }
    }
}

function Wait-BackendPortFree {
    param([int]$TimeoutSeconds = 20)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if (@(Get-BackendListenerProcessIds).Count -eq 0) {
            return
        }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $deadline)

    throw "Port 8000 is still listening after stopping '$taskName'."
}

function Register-BackendTask {
    param([Parameter(Mandatory = $true)][string]$PythonPath)

    $action = New-ScheduledTaskAction `
        -Execute $PythonPath `
        -Argument '-m uvicorn app.main:app --host 0.0.0.0 --port 8000' `
        -WorkingDirectory $serverRoot
    $trigger = New-ScheduledTaskTrigger -AtStartup
    $principal = New-ScheduledTaskPrincipal `
        -UserId "$env:USERDOMAIN\$env:USERNAME" `
        -LogonType S4U `
        -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero)

    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Force | Out-Null
}

function Start-BackendTask {
    Start-ScheduledTask -TaskName $taskName
}

function Wait-BackendReady {
    param([int]$TimeoutSeconds = 60)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($task -and $task.State -eq 'Running') {
            try {
                $response = Invoke-WebRequest `
                    -Uri 'http://127.0.0.1:8000/' `
                    -TimeoutSec 2 `
                    -UseBasicParsing
                if ($response.StatusCode -eq 200) {
                    $task = Get-ScheduledTask -TaskName $taskName
                    if ($task.State -eq 'Running') {
                        return
                    }
                }
            }
            catch {
                # Wait for Uvicorn and application startup to finish.
            }
        }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $deadline)

    throw "Backend did not return HTTP 200 on port 8000 within $TimeoutSeconds seconds."
}

function Remove-PreviousVirtualEnvironment {
    param([string]$PythonPath)

    if ([string]::IsNullOrWhiteSpace($PythonPath)) {
        return
    }

    $scriptsPath = Split-Path -Parent $PythonPath
    $environmentPath = Split-Path -Parent $scriptsPath
    $normalizedEnvironment = [IO.Path]::GetFullPath($environmentPath).TrimEnd('\')
    $normalizedVenvs = [IO.Path]::GetFullPath($venvsPath).TrimEnd('\')
    $normalizedLegacyVenv = [IO.Path]::GetFullPath((Join-Path $serverRoot '.venv')).TrimEnd('\')

    if ($normalizedEnvironment -eq $deploymentVenvPath.TrimEnd('\')) {
        return
    }
    if ($normalizedEnvironment -eq $normalizedLegacyVenv -or
        $normalizedEnvironment.StartsWith($normalizedVenvs + '\', [StringComparison]::OrdinalIgnoreCase)) {
        if (Test-Path -LiteralPath $normalizedEnvironment -PathType Container) {
            Remove-Item -LiteralPath $normalizedEnvironment -Recurse -Force
        }
    }
}

if (-not (Test-Path -LiteralPath $serverRoot -PathType Container)) {
    throw "Backend directory does not exist: $serverRoot"
}
if (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf)) {
    throw "Backend archive does not exist: $ArchivePath"
}

try {
    if (Test-Path -LiteralPath $stagingPath) {
        Remove-Item -LiteralPath $stagingPath -Recurse -Force
    }
    New-Item -ItemType Directory -Path $stagingPath | Out-Null
    Expand-Archive -LiteralPath $ArchivePath -DestinationPath $stagingPath -Force

    $stagedAppPath = Join-Path $stagingPath 'app'
    $stagedRequirementsPath = Join-Path $stagingPath 'requirements.txt'
    if (-not (Test-Path -LiteralPath $stagedAppPath -PathType Container)) {
        throw 'Backend archive is missing app/.'
    }
    if (-not (Test-Path -LiteralPath $stagedRequirementsPath -PathType Leaf)) {
        throw 'Backend archive is missing requirements.txt.'
    }

    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        if (-not $existingTask.Actions -or [string]::IsNullOrWhiteSpace($existingTask.Actions[0].Execute)) {
            throw "Cannot determine the existing Python executable for task '$taskName'; refusing an unsafe deployment."
        }
        $previousPython = $existingTask.Actions[0].Execute
    }
    Assert-BackendListenerManaged -Task $existingTask

    $python = Get-Command 'python.exe' -ErrorAction Stop
    & $python.Source -c "import sys; raise SystemExit(1 if sys.version_info < (3, 10) else 0)"
    if ($LASTEXITCODE -ne 0) {
        throw 'Python 3.10 or later is required to deploy the backend.'
    }

    New-Item -ItemType Directory -Path $venvsPath -Force | Out-Null
    & $python.Source -m venv $deploymentVenvPath
    if ($LASTEXITCODE -ne 0) {
        throw 'Creating the isolated backend virtual environment failed.'
    }

    & $deploymentPython -m pip install --disable-pip-version-check -r $stagedRequirementsPath
    if ($LASTEXITCODE -ne 0) {
        throw 'Installing backend requirements into the isolated environment failed.'
    }

    Stop-BackendTask
    Wait-BackendPortFree

    $previousAppExists = Test-Path -LiteralPath $liveAppPath
    $previousRequirementsExist = Test-Path -LiteralPath $requirementsPath

    try {
        if (Test-Path -LiteralPath $appBackupPath) {
            Remove-Item -LiteralPath $appBackupPath -Recurse -Force
        }
        if (Test-Path -LiteralPath $requirementsBackupPath) {
            Remove-Item -LiteralPath $requirementsBackupPath -Force
        }
        if ($previousAppExists) {
            Move-Item -LiteralPath $liveAppPath -Destination $appBackupPath
        }
        if ($previousRequirementsExist) {
            Copy-Item -LiteralPath $requirementsPath -Destination $requirementsBackupPath
        }

        Move-Item -LiteralPath $stagedAppPath -Destination $liveAppPath
        $newAppInstalled = $true
        Copy-Item -LiteralPath $stagedRequirementsPath -Destination $requirementsPath -Force
        $deploymentTaskMayUseVenv = $true
        Register-BackendTask -PythonPath $deploymentPython
        Start-BackendTask
        Wait-BackendReady
        $deploymentCommitted = $true
    }
    catch {
        $deploymentError = $_
        try {
            Stop-BackendTask
            Wait-BackendPortFree
            if ($newAppInstalled -and (Test-Path -LiteralPath $liveAppPath)) {
                Remove-Item -LiteralPath $liveAppPath -Recurse -Force
            }
            if (Test-Path -LiteralPath $appBackupPath) {
                Move-Item -LiteralPath $appBackupPath -Destination $liveAppPath
            }
            if (Test-Path -LiteralPath $requirementsBackupPath) {
                Copy-Item -LiteralPath $requirementsBackupPath -Destination $requirementsPath -Force
                Remove-Item -LiteralPath $requirementsBackupPath -Force
            }
            elseif (-not $previousRequirementsExist -and (Test-Path -LiteralPath $requirementsPath)) {
                Remove-Item -LiteralPath $requirementsPath -Force
            }
            if ($previousPython) {
                Register-BackendTask -PythonPath $previousPython
                $deploymentTaskMayUseVenv = $false
                Start-BackendTask
                Wait-BackendReady
            }
            else {
                Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
                $remainingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
                if ($remainingTask) {
                    throw "Failed to remove the first-deployment scheduled task '$taskName'; its Python environment will be retained."
                }
                $deploymentTaskMayUseVenv = $false
            }
        }
        catch {
            throw "Backend deployment failed ($deploymentError). Rollback also failed ($($_.Exception.Message)); inspect scheduled task '$taskName' and $serverRoot."
        }
        throw $deploymentError
    }

    if ($deploymentCommitted) {
        try {
            if (Test-Path -LiteralPath $appBackupPath) {
                Remove-Item -LiteralPath $appBackupPath -Recurse -Force
            }
            if (Test-Path -LiteralPath $requirementsBackupPath) {
                Remove-Item -LiteralPath $requirementsBackupPath -Force
            }
            Remove-PreviousVirtualEnvironment -PythonPath $previousPython
        }
        catch {
            Write-Warning "Deployment succeeded, but previous deployment files could not be fully cleaned up: $($_.Exception.Message)"
        }
    }
}
finally {
    if (Test-Path -LiteralPath $stagingPath) {
        Remove-Item -LiteralPath $stagingPath -Recurse -Force
    }
    if (Test-Path -LiteralPath $ArchivePath) {
        Remove-Item -LiteralPath $ArchivePath -Force
    }
    if (-not $deploymentCommitted -and -not $deploymentTaskMayUseVenv -and
        (Test-Path -LiteralPath $deploymentVenvPath -PathType Container)) {
        Remove-Item -LiteralPath $deploymentVenvPath -Recurse -Force
    }
}
