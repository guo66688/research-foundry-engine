param(
    [string]$Destination = "$env:USERPROFILE\\.codex\\skills",
    [string]$VenvPath = "$env:USERPROFILE\\.codex\\venvs\\research-foundry-standalone",
    [string[]]$Skill = @(
        "source-intake",
        "candidate-triage",
        "evidence-dossier",
        "knowledge-synthesis",
        "run-registry"
    ),
    [switch]$InstallDeps,
    [switch]$RecreateVenv,
    [string]$BootstrapPython = "python"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Get-VenvPythonPath {
    param([string]$Path)
    return Join-Path $Path "Scripts\python.exe"
}

function Ensure-Venv {
    param(
        [string]$Path,
        [string]$Bootstrap,
        [switch]$Recreate
    )

    if ($Recreate -and (Test-Path $Path)) {
        Remove-Item -Path $Path -Recurse -Force
    }

    $venvPython = Get-VenvPythonPath -Path $Path
    if (-not (Test-Path $venvPython)) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $Path) -Force | Out-Null
        & $Bootstrap -m venv $Path
        if ($LASTEXITCODE -ne 0) {
            throw "Virtual environment creation failed."
        }
    }

    return $venvPython
}

New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$runtimePython = $null

if ($InstallDeps -or (Test-Path (Get-VenvPythonPath -Path $VenvPath)) -or $RecreateVenv) {
    $runtimePython = Ensure-Venv -Path $VenvPath -Bootstrap $BootstrapPython -Recreate:$RecreateVenv
}

$supportSource = Join-Path $root ".internal"
$supportTarget = Join-Path $Destination ".internal"
if (Test-Path $supportSource) {
    if (Test-Path $supportTarget) {
        Remove-Item -Path $supportTarget -Recurse -Force
    }
    Copy-Item -Path $supportSource -Destination $supportTarget -Recurse -Force
    if ($runtimePython) {
        $supportRuntimeDir = Join-Path $supportTarget "research-foundry\.runtime"
        New-Item -ItemType Directory -Path $supportRuntimeDir -Force | Out-Null
        $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText((Join-Path $supportRuntimeDir "python.txt"), $runtimePython, $utf8NoBom)
    }
}

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
    if ($runtimePython) {
        $runtimeDir = Join-Path $target ".runtime"
        New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
        $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText((Join-Path $runtimeDir "python.txt"), $runtimePython, $utf8NoBom)
    }
    Write-Host "Installed $name -> $target"
}

if ($InstallDeps) {
    if (-not $runtimePython) {
        $runtimePython = Ensure-Venv -Path $VenvPath -Bootstrap $BootstrapPython -Recreate:$RecreateVenv
    }
    & $runtimePython -m pip install -r (Join-Path $root "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }
}
