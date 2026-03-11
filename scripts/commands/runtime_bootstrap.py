from __future__ import annotations

import os
import sys
from pathlib import Path


def _requested_mode(argv: list[str]) -> str:
    for index, token in enumerate(argv):
        if token == "--mode" and index + 1 < len(argv):
            return argv[index + 1].strip().lower()
        if token.startswith("--mode="):
            return token.split("=", 1)[1].strip().lower()
    return ""


def _same_python(current: str, recorded: str) -> bool:
    try:
        return Path(current).resolve() == Path(recorded).resolve()
    except OSError:
        return os.path.normcase(os.path.abspath(current)) == os.path.normcase(os.path.abspath(recorded))


def maybe_reexec_for_runtime(script_file: str, argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if _requested_mode(args) == "external":
        return

    support_root = Path(script_file).resolve().parent.parent
    runtime_file = support_root / ".runtime" / "python.txt"
    if not runtime_file.exists():
        return

    recorded = runtime_file.read_text(encoding="utf-8").lstrip("\ufeff").strip()
    if not recorded:
        return
    if not Path(recorded).exists():
        return
    if _same_python(sys.executable, recorded):
        return

    os.execv(recorded, [recorded, str(Path(script_file).resolve()), *args])
