from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = REPO_ROOT / ".agents" / "skills"
HANDOFF_MATRIX = SKILLS_ROOT / "references" / "handoff-matrix.md"
OUTPUT_ROOT = REPO_ROOT / "standalone-skills"

SKILL_ORDER = [
    "source-intake",
    "candidate-triage",
    "evidence-dossier",
    "knowledge-synthesis",
    "run-registry",
]


@dataclass(frozen=True)
class FileSpec:
    source: Path
    destination: str
    replacements: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class SkillSpec:
    command_path: str
    standalone_note: str
    files: tuple[FileSpec, ...]


def _file_spec(source: str, destination: str, *replacements: tuple[str, str]) -> FileSpec:
    return FileSpec(source=REPO_ROOT / source, destination=destination, replacements=replacements)


SKILL_SPECS = {
    "source-intake": SkillSpec(
        command_path="python scripts/flow_intake_fetch.py",
        standalone_note=(
            "## standalone execution\n\n"
            "- This skill bundles its own `scripts/` and can be executed directly inside the skill directory.\n"
            "- It does not depend on external `research-foundry-engine` Python import paths.\n"
        ),
        files=(
            _file_spec(
                "scripts/intake/flow_intake_fetch.py",
                "scripts/flow_intake_fetch.py",
                ("ROOT = Path(__file__).resolve().parents[2]", "ROOT = Path(__file__).resolve().parent"),
                ("from scripts.shared.flow_common import", "from rf_standalone.flow_common import"),
                ("from scripts.shared.flow_sources import", "from rf_standalone.flow_sources import"),
            ),
            _file_spec("scripts/shared/flow_common.py", "scripts/rf_standalone/flow_common.py"),
            _file_spec(
                "scripts/shared/flow_sources.py",
                "scripts/rf_standalone/flow_sources.py",
                ("from scripts.shared.flow_common import", "from rf_standalone.flow_common import"),
            ),
        ),
    ),
    "candidate-triage": SkillSpec(
        command_path="python scripts/flow_triage_rank.py",
        standalone_note=(
            "## standalone execution\n\n"
            "- This skill bundles its own `scripts/` and can be executed directly inside the skill directory.\n"
            "- It does not depend on external `research-foundry-engine` Python import paths.\n"
        ),
        files=(
            _file_spec(
                "scripts/triage/flow_triage_rank.py",
                "scripts/flow_triage_rank.py",
                ("ROOT = Path(__file__).resolve().parents[2]", "ROOT = Path(__file__).resolve().parent"),
                ("from scripts.shared.flow_common import", "from rf_standalone.flow_common import"),
            ),
            _file_spec("scripts/shared/flow_common.py", "scripts/rf_standalone/flow_common.py"),
        ),
    ),
    "evidence-dossier": SkillSpec(
        command_path="python scripts/flow_dossier_build.py",
        standalone_note=(
            "## standalone execution\n\n"
            "- This skill bundles its own `scripts/` and can be executed directly inside the skill directory.\n"
            "- Figure extraction logic is shipped with the skill and does not depend on external `research-foundry-engine` imports.\n"
        ),
        files=(
            _file_spec(
                "scripts/dossier/flow_dossier_build.py",
                "scripts/flow_dossier_build.py",
                ("ROOT = Path(__file__).resolve().parents[2]", "ROOT = Path(__file__).resolve().parent"),
                ("from scripts.dossier.flow_dossier_figures import", "from rf_standalone.flow_dossier_figures import"),
                ("from scripts.shared.flow_common import", "from rf_standalone.flow_common import"),
            ),
            _file_spec("scripts/shared/flow_common.py", "scripts/rf_standalone/flow_common.py"),
            _file_spec(
                "scripts/dossier/flow_dossier_figures.py",
                "scripts/rf_standalone/flow_dossier_figures.py",
                ("ROOT = Path(__file__).resolve().parents[2]", "ROOT = Path(__file__).resolve().parents[1]"),
                ("from scripts.shared.flow_common import", "from rf_standalone.flow_common import"),
                ("from scripts.shared.flow_sources import", "from rf_standalone.flow_sources import"),
            ),
            _file_spec(
                "scripts/shared/flow_sources.py",
                "scripts/rf_standalone/flow_sources.py",
                ("from scripts.shared.flow_common import", "from rf_standalone.flow_common import"),
            ),
        ),
    ),
    "knowledge-synthesis": SkillSpec(
        command_path="python scripts/flow_synthesis_link.py",
        standalone_note=(
            "## standalone execution\n\n"
            "- This skill bundles its own `scripts/` and can be executed directly inside the skill directory.\n"
            "- It does not depend on external `research-foundry-engine` Python import paths.\n"
        ),
        files=(
            _file_spec(
                "scripts/synthesis/flow_synthesis_link.py",
                "scripts/flow_synthesis_link.py",
                ("ROOT = Path(__file__).resolve().parents[2]", "ROOT = Path(__file__).resolve().parent"),
                ("from scripts.shared.flow_common import", "from rf_standalone.flow_common import"),
                ("from scripts.shared.flow_notes import", "from rf_standalone.flow_notes import"),
                ("from scripts.shared.flow_relations import", "from rf_standalone.flow_relations import"),
            ),
            _file_spec("scripts/shared/flow_common.py", "scripts/rf_standalone/flow_common.py"),
            _file_spec(
                "scripts/shared/flow_notes.py",
                "scripts/rf_standalone/flow_notes.py",
                ("from scripts.shared.flow_common import", "from rf_standalone.flow_common import"),
            ),
            _file_spec(
                "scripts/shared/flow_relations.py",
                "scripts/rf_standalone/flow_relations.py",
                ("from scripts.shared.flow_common import", "from rf_standalone.flow_common import"),
            ),
        ),
    ),
    "run-registry": SkillSpec(
        command_path="python scripts/flow_registry_update.py",
        standalone_note=(
            "## standalone execution\n\n"
            "- This skill bundles its own `scripts/` and can be executed directly inside the skill directory.\n"
            "- It does not depend on external `research-foundry-engine` Python import paths.\n"
        ),
        files=(
            _file_spec(
                "scripts/registry/flow_registry_update.py",
                "scripts/flow_registry_update.py",
                ("ROOT = Path(__file__).resolve().parents[2]", "ROOT = Path(__file__).resolve().parent"),
                ("from scripts.shared.flow_common import", "from rf_standalone.flow_common import"),
            ),
            _file_spec("scripts/shared/flow_common.py", "scripts/rf_standalone/flow_common.py"),
        ),
    ),
}


def copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def copy_text_file(file_spec: FileSpec, destination_root: Path) -> None:
    destination = destination_root / file_spec.destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = file_spec.source.read_text(encoding="utf-8")
    for old, new in file_spec.replacements:
        if old not in content:
            raise ValueError(f"expected text not found in {file_spec.source}: {old}")
        content = content.replace(old, new)
    destination.write_text(content, encoding="utf-8")


def rewrite_skill_markdown(skill_root: Path, spec: SkillSpec, source_skill_name: str) -> None:
    skill_md = skill_root / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")

    command_replacements = {
        "source-intake": "python scripts/intake/flow_intake_fetch.py",
        "candidate-triage": "python scripts/triage/flow_triage_rank.py",
        "evidence-dossier": "python scripts/dossier/flow_dossier_build.py",
        "knowledge-synthesis": "python scripts/synthesis/flow_synthesis_link.py",
        "run-registry": "python scripts/registry/flow_registry_update.py",
    }
    original_command = command_replacements[source_skill_name]
    if original_command not in content:
        raise ValueError(f"expected command not found in {skill_md}: {original_command}")
    content = content.replace(original_command, spec.command_path)
    content = content.replace("`../references/handoff-matrix.md`", "`references/handoff-matrix.md`")

    if "## standalone execution" not in content:
        content = content.rstrip() + "\n\n" + spec.standalone_note

    skill_md.write_text(content, encoding="utf-8")


def write_install_ps1(output_root: Path) -> None:
    content = """param(
    [string]$Destination = "$env:USERPROFILE\\\\.codex\\\\skills",
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
"""
    (output_root / "install-standalone-skills.ps1").write_text(content, encoding="utf-8", newline="\n")


def write_install_sh(output_root: Path) -> None:
    content = """#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESTINATION="$HOME/.codex/skills"
INSTALL_DEPS=false
PYTHON_BIN="python"
SKILLS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --destination)
      DESTINATION="$2"
      shift 2
      ;;
    --install-deps)
      INSTALL_DEPS=true
      shift
      ;;
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do
        SKILLS+=("$1")
        shift
      done
      ;;
    *)
      SKILLS+=("$1")
      shift
      ;;
  esac
done

if [ "${#SKILLS[@]}" -eq 0 ]; then
  SKILLS=(
    "source-intake"
    "candidate-triage"
    "evidence-dossier"
    "knowledge-synthesis"
    "run-registry"
  )
fi

mkdir -p "$DESTINATION"

for name in "${SKILLS[@]}"; do
  SOURCE="$ROOT/$name"
  TARGET="$DESTINATION/$name"
  if [ ! -d "$SOURCE" ]; then
    echo "Skill not found: $name" >&2
    exit 1
  fi
  rm -rf "$TARGET"
  cp -R "$SOURCE" "$TARGET"
  echo "Installed $name -> $TARGET"
done

if [ "$INSTALL_DEPS" = true ]; then
  "$PYTHON_BIN" -m pip install -r "$ROOT/requirements.txt"
fi
"""
    (output_root / "install-standalone-skills.sh").write_text(content, encoding="utf-8", newline="\n")


def build_skill(skill_name: str, output_root: Path) -> None:
    spec = SKILL_SPECS[skill_name]
    source_skill_root = SKILLS_ROOT / skill_name
    destination_root = output_root / skill_name

    copy_tree(source_skill_root, destination_root)
    shutil.copy2(HANDOFF_MATRIX, destination_root / "references" / "handoff-matrix.md")

    scripts_root = destination_root / "scripts"
    if scripts_root.exists():
        shutil.rmtree(scripts_root)
    scripts_root.mkdir(parents=True, exist_ok=True)

    for file_spec in spec.files:
        copy_text_file(file_spec, destination_root)

    (destination_root / "scripts" / "rf_standalone" / "__init__.py").write_text("", encoding="utf-8")
    rewrite_skill_markdown(destination_root, spec, skill_name)


def build(output_root: Path) -> None:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    for skill_name in SKILL_ORDER:
        build_skill(skill_name, output_root)

    shutil.copy2(REPO_ROOT / "requirements.txt", output_root / "requirements.txt")
    write_install_ps1(output_root)
    write_install_sh(output_root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build standalone Codex skills from repo skills and engine scripts.")
    parser.add_argument(
        "--output",
        default=str(OUTPUT_ROOT),
        help="Directory to write the generated standalone skills into.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build(Path(args.output))
    print(f"standalone_skills={Path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
