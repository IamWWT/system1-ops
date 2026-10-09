"""Run the same commit gates on Linux and Windows with explicit failure exits."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    python = sys.executable
    commands = [
        [python, "-m", "ruff", "check", "."],
        [python, "-m", "ruff", "format", "--check", "."],
        [python, "-m", "mypy", "src/system1_ops"],
        [python, "-m", "coverage", "run", "-m", "pytest", "-q"],
        [python, "-m", "coverage", "report", "--fail-under=35"],
        [python, str(ROOT / "scripts/doc_check.py")],
        ["clang-format", "--dry-run", "--Werror", "native/engine.cpp"],
        ["node", "--check", "src/system1_ops/web/app.js"],
        ["uv", "build", "--out-dir", "dist"],
    ]
    if os.name != "nt":
        commands.append(["bash", "-n", "system1.sh", "setup-runtime.sh"])
    exported = subprocess.run(
        ["uv", "export", "--locked", "--no-dev", "--no-emit-project", "--no-hashes", "--no-header"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if exported.returncode or exported.stdout != (ROOT / "requirements-http.txt").read_text(encoding="utf-8"):
        print("requirements-http.txt differs from uv.lock export", file=sys.stderr)
        return 1
    for command in commands:
        if not shutil.which(command[0]):
            print(f"Missing gate dependency: {command[0]}", file=sys.stderr)
            return 1
        print("+ " + " ".join(command), flush=True)
        result = subprocess.run(command, cwd=ROOT)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
