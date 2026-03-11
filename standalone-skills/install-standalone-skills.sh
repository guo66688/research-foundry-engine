#!/usr/bin/env bash
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
