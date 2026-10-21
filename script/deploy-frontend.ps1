# GitHub Actions가 SSH로 프론트엔드 Windows 서버에서 실행하는 배포 스크립트.
# 업로드된 빌드 결과물을 Nginx html 폴더에 반영한다. 정적 파일이라 Nginx 재시작은 필요 없다.
param(
    [Parameter(Mandatory = $true)][string]$StagingDir,
    [Parameter(Mandatory = $true)][string]$HtmlDir
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path (Join-Path $StagingDir "index.html"))) {
    throw "Staged frontend build not found: $StagingDir\index.html"
}
New-Item -ItemType Directory -Force -Path $HtmlDir | Out-Null

# /MIR: 이전 빌드의 남은 파일까지 정리. Nginx 기본 에러 페이지(50x.html)는 유지.
& robocopy.exe $StagingDir $HtmlDir /MIR /XF 50x.html /R:3 /W:2 /NFL /NDL /NP | Out-Host
# robocopy 종료 코드 0~7은 성공, 8 이상은 실패
if ($LASTEXITCODE -ge 8) {
    throw "robocopy failed with exit code $LASTEXITCODE"
}
# 다음 업로드에 이전 파일이 섞이지 않도록 업로드 폴더 정리 (StagingDir = <업로드 폴더>\frontend\dist)
Remove-Item (Split-Path (Split-Path $StagingDir -Parent) -Parent) -Recurse -Force
Write-Host "Frontend deployed to $HtmlDir"
exit 0
