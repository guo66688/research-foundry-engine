param(
    [string]$Destination = "$env:USERPROFILE\\.codex\\skills",
    [string[]]$Skill = @(
        "source-intake",
        "candidate-triage",
        "evidence-dossier",
        "knowledge-synthesis",
        "run-registry"
    ),
    [switch]$InstallDeps,
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
New-Item -ItemType Directory -Path $Destination -Force | Out-Null

foreach ($name in $Skill) {
    $source = Join-Path $root $name
    if (-not (Test-Path $source)) {
        throw "Skill not found: $name"
    }

    $target = Join-Path $Destination $name
    if (Test-Path $target) {
        Remove-Item -Path $target -Recurse -Force
    }

    Copy-Item -Path $source -Destination $target -Recurse -Force
    Write-Host "Installed $name -> $target"
}

if ($InstallDeps) {
    & $PythonExe -m pip install -r (Join-Path $root "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }
}
