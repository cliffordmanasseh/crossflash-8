#!/usr/bin/env python3
"""Fail if any firmware (or firmware-derived blob) is present in the repository.

Run manually:
    python3 tools/check_no_firmware.py

Or let the pre-commit hook run it:
    git config core.hooksPath .githooks
"""
from __future__ import annotations
import os
import subprocess
import sys

FORBIDDEN_EXT = {
    ".syx", ".bin", ".hex", ".s19", ".srec", ".mot", ".elf", ".zip", ".7z", ".tar",
    ".gz", ".xz", ".rom", ".img", ".dump",
}
# a .syx starts with F0 00 21 07 ; a firmware blob is large and non-text
MODAL_MAGIC = bytes([0xF0, 0x00, 0x21, 0x07])
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", "out", "dist"}


def tracked_files() -> list[str]:
    try:
        out = subprocess.check_output(["git", "ls-files"], text=True)
        return [ln for ln in out.splitlines() if ln.strip()]
    except Exception:
        return []


def walk(root: str) -> list[str]:
    found = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            found.append(os.path.join(base, f))
    return found


def looks_like_firmware(path: str) -> str | None:
    ext = os.path.splitext(path)[1].lower()
    if ext in FORBIDDEN_EXT:
        return f"forbidden extension {ext}"
    try:
        if os.path.getsize(path) > 1 << 20:              # >1 MiB
            with open(path, "rb") as fh:
                if fh.read(4) == MODAL_MAGIC:
                    return "Modal SysEx magic in a large file"
    except OSError:
        pass
    return None


def main() -> int:
    problems = []
    for path in tracked_files():
        r = looks_like_firmware(path)
        if r:
            problems.append(f"tracked: {path} ({r})")
    for path in walk("."):
        if os.sep + "." in path or "/." in path:
            continue
        r = looks_like_firmware(path)
        if r:
            problems.append(f"present: {path} ({r})")

    if problems:
        print("FIRMWARE GUARD: refusing — firmware must never be committed:\n")
        for p in sorted(set(problems)):
            print("  " + p)
        print("\nSee docs/SCOPE.md. Remove these files and try again.")
        return 1
    print("firmware guard: OK (no firmware blobs found)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
