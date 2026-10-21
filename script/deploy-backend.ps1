# GitHub Actions가 SSH로 백엔드 Windows 서버에서 실행하는 배포 스크립트.
# 기존 Uvicorn 종료 -> 코드 교체 -> 의존성 설치 -> Uvicorn 재시작 순서로 동작한다.
param(
    [Parameter(Mandatory = $true)][string]$StagingDir,
    [Parameter(Mandatory = $true)][string]$BackendDir,
    [int]$Port = 443,
    # BackendDir 기준 상대 경로. 두 파일이 모두 있으면 HTTPS로 실행한다.
    [string]$SslCertFile = "certs\certificate.crt",
    [string]$SslKeyFile = "certs\private.key",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

function Stop-ProcessTree([int]$ProcessId) {
    if (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue) {
        Write-Host "Stopping process tree $ProcessId"
        & taskkill.exe /PID $ProcessId /T /F | Out-Host
    }
}

function Invoke-Native([string]$FilePath, [string[]]$Arguments) {
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path (Join-Path $StagingDir "app"))) {
    throw "Staged backend code not found: $StagingDir\app"
}
New-Item -ItemType Directory -Force -Path $BackendDir | Out-Null

# 1. 기존 서버 종료 (PID 파일 + 포트 점유 프로세스)
$pidFile = Join-Path $BackendDir "backend.pid"
if (Test-Path $pidFile) {
    $oldPid = (Get-Content $pidFile -Raw).Trim()
    if ($oldPid -match '^\d+$') {
        Stop-ProcessTree ([int]$oldPid)
    }
    Remove-Item $pidFile -Force
}
$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
foreach ($owner in ($listeners | Select-Object -ExpandProperty OwningProcess -Unique)) {
    Stop-ProcessTree ([int]$owner)
}
for ($i = 0; $i -lt 20; $i++) {
    if (-not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) { break }
    Start-Sleep -Seconds 1
}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $Port is still in use. Stop the existing server manually (it may be owned by another user)."
}

# 2. 코드 교체 (.env, app.db, .venv, 로그는 유지)
$appDir = Join-Path $BackendDir "app"
if (Test-Path $appDir) {
    Remove-Item $appDir -Recurse -Force
}
Copy-Item (Join-Path $StagingDir "app") $appDir -Recurse -Force
Copy-Item (Join-Path $StagingDir "requirements.txt") (Join-Path $BackendDir "requirements.txt") -Force
# 다음 업로드에 이전 파일이 섞이지 않도록 업로드 폴더 정리
Remove-Item $StagingDir -Recurse -Force

# 3. 가상환경 및 의존성
$venvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment with $Python"
    Invoke-Native $Python @("-m", "venv", (Join-Path $BackendDir ".venv"))
}
Invoke-Native $venvPython @("-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", (Join-Path $BackendDir "requirements.txt"))

# 4. 서버 시작
# 환경변수(KAKAO_*, JWT_SECRET_KEY 등)는 BackendDir\.env 에서 앱이 읽는다.
if (-not (Test-Path (Join-Path $BackendDir ".env"))) {
    Write-Warning "$BackendDir\.env not found. The app will start with default settings."
}
$uvicornArgs = "-m uvicorn app.main:app --host 0.0.0.0 --port $Port"
if ((Test-Path (Join-Path $BackendDir $SslCertFile)) -and (Test-Path (Join-Path $BackendDir $SslKeyFile))) {
    $uvicornArgs += " --ssl-certfile `"$SslCertFile`" --ssl-keyfile `"$SslKeyFile`""
} else {
    Write-Warning "SSL certificate not found under $BackendDir. Starting without HTTPS."
}
# SSH 세션에서 띄운 프로세스는 세션 종료 시 함께 종료되므로 WMI(Win32_Process)로 분리해서 실행한다.
$logFile = Join-Path $BackendDir "backend.log"
$commandLine = "cmd.exe /c `"`"$venvPython`" $uvicornArgs >> `"$logFile`" 2>&1`""
$result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine      = $commandLine
    CurrentDirectory = $BackendDir
}
if ($result.ReturnValue -ne 0) {
    throw "Failed to start backend (Win32_Process.Create returned $($result.ReturnValue))"
}
Set-Content -Path $pidFile -Value $result.ProcessId -Encoding ascii
Write-Host "Backend started (pid $($result.ProcessId)) on port $Port"

# 5. 기동 확인
for ($i = 0; $i -lt 30; $i++) {
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
        Write-Host "Backend is listening on port $Port"
        exit 0
    }
    Start-Sleep -Seconds 1
}
Write-Host "Backend did not start listening on port $Port. Last log lines:"
if (Test-Path $logFile) { Get-Content $logFile -Tail 50 | Out-Host }
exit 1
