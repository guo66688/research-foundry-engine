#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESTINATION="$HOME/.codex/skills"
VENV_PATH="$HOME/.codex/venvs/research-foundry-standalone"
INSTALL_DEPS=false
RECREATE_VENV=false
BOOTSTRAP_PYTHON="python"
SKILLS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --destination)
      DESTINATION="$2"
      shift 2
      ;;
    --venv)
      VENV_PATH="$2"
      shift 2
      ;;
    --install-deps)
      INSTALL_DEPS=true
      shift
      ;;
    --recreate-venv)
      RECREATE_VENV=true
      shift
      ;;
    --python|--bootstrap-python)
      BOOTSTRAP_PYTHON="$2"
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

venv_python_path() {
  printf '%s
' "$1/bin/python"
}

ensure_venv() {
  local path="$1"
  local bootstrap="$2"
  local venv_python
  venv_python="$(venv_python_path "$path")"

  if [ "$RECREATE_VENV" = true ] && [ -d "$path" ]; then
    rm -rf "$path"
  fi

  if [ ! -x "$venv_python" ]; then
    mkdir -p "$(dirname "$path")"
    "$bootstrap" -m venv "$path"
  fi

  venv_python="$(venv_python_path "$path")"
  if [ ! -x "$venv_python" ]; then
    echo "Virtual environment creation failed: $path" >&2
    exit 1
  fi

  printf '%s
' "$venv_python"
}

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
RUNTIME_PYTHON=""

if [ "$INSTALL_DEPS" = true ] || [ "$RECREATE_VENV" = true ] || [ -x "$(venv_python_path "$VENV_PATH")" ]; then
  RUNTIME_PYTHON="$(ensure_venv "$VENV_PATH" "$BOOTSTRAP_PYTHON")"
fi

SUPPORT_SOURCE="$ROOT/.internal"
SUPPORT_TARGET="$DESTINATION/.internal"
if [ -d "$SUPPORT_SOURCE" ]; then
  rm -rf "$SUPPORT_TARGET"
  cp -R "$SUPPORT_SOURCE" "$SUPPORT_TARGET"
fi

for name in "${SKILLS[@]}"; do
  SOURCE="$ROOT/$name"
  TARGET="$DESTINATION/$name"
  if [ ! -d "$SOURCE" ]; then
    echo "Skill not found: $name" >&2
    exit 1
  fi
  rm -rf "$TARGET"
  cp -R "$SOURCE" "$TARGET"
  if [ -n "$RUNTIME_PYTHON" ]; then
    mkdir -p "$TARGET/.runtime"
    printf '%s
' "$RUNTIME_PYTHON" > "$TARGET/.runtime/python.txt"
  fi
  echo "Installed $name -> $TARGET"
done

if [ "$INSTALL_DEPS" = true ]; then
  if [ -z "$RUNTIME_PYTHON" ]; then
    RUNTIME_PYTHON="$(ensure_venv "$VENV_PATH" "$BOOTSTRAP_PYTHON")"
  fi
  "$RUNTIME_PYTHON" -m pip install -r "$ROOT/requirements.txt"
fi
