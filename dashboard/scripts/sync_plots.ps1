param(
  [string]$Source = "..\\plots",
  [string]$Dest = ".\\public\\plots"
)

$ErrorActionPreference = "Stop"

$srcPath = Resolve-Path $Source
$destPath = Join-Path (Get-Location) $Dest

if (-not (Test-Path $destPath)) {
  New-Item -ItemType Directory -Force -Path $destPath | Out-Null
}

Copy-Item -Path (Join-Path $srcPath "*.png") -Destination $destPath -Force -ErrorAction SilentlyContinue

Write-Host "Synced plots from $srcPath to $destPath"

