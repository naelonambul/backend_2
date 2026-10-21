param(
    [string]$ArchivePath = 'C:\Users\test\Downloads\nginx-1.30.5\_frontend-deploy.zip'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$nginxRoot = 'C:\Users\test\Downloads\nginx-1.30.5'
$htmlPath = Join-Path $nginxRoot 'html'
$stagingPath = Join-Path $nginxRoot '_frontend-stage'

if (-not (Test-Path -LiteralPath $htmlPath -PathType Container)) {
    throw "Nginx document root does not exist: $htmlPath"
}
if (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf)) {
    throw "Frontend archive does not exist: $ArchivePath"
}

try {
    if (Test-Path -LiteralPath $stagingPath) {
        Remove-Item -LiteralPath $stagingPath -Recurse -Force
    }
    New-Item -ItemType Directory -Path $stagingPath | Out-Null
    Expand-Archive -LiteralPath $ArchivePath -DestinationPath $stagingPath -Force

    $stagedIndexPath = Join-Path $stagingPath 'index.html'
    if (-not (Test-Path -LiteralPath $stagedIndexPath -PathType Leaf)) {
        throw 'Frontend archive is missing index.html.'
    }

    $stagedAssetsPath = Join-Path $stagingPath 'assets'
    if (Test-Path -LiteralPath $stagedAssetsPath -PathType Container) {
        $htmlAssetsPath = Join-Path $htmlPath 'assets'
        New-Item -ItemType Directory -Force -Path $htmlAssetsPath | Out-Null
        Copy-Item -Path (Join-Path $stagedAssetsPath '*') -Destination $htmlAssetsPath -Recurse -Force
    }

    Get-ChildItem -LiteralPath $stagingPath -File |
        Where-Object { $_.Name -ne 'index.html' } |
        ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $htmlPath -Force
        }

    Get-ChildItem -LiteralPath $stagingPath -Directory |
        Where-Object { $_.Name -ne 'assets' } |
        ForEach-Object {
            $destinationPath = Join-Path $htmlPath $_.Name
            New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null
            Copy-Item -Path (Join-Path $_.FullName '*') -Destination $destinationPath -Recurse -Force
        }

    $temporaryIndexPath = Join-Path $htmlPath 'index.html.deploying'
    Copy-Item -LiteralPath $stagedIndexPath -Destination $temporaryIndexPath -Force
    Move-Item -LiteralPath $temporaryIndexPath -Destination (Join-Path $htmlPath 'index.html') -Force
}
finally {
    if (Test-Path -LiteralPath $stagingPath) {
        Remove-Item -LiteralPath $stagingPath -Recurse -Force
    }
    if (Test-Path -LiteralPath $ArchivePath) {
        Remove-Item -LiteralPath $ArchivePath -Force
    }
}
