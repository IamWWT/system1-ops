"""Maintained workspace inventory and root ownership checks."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {
    "README.md",
    "AGENTS.md",
    "MEMORY.md",
    "CHANGELOG.md",
    "LICENSE",
    "pyproject.toml",
    "uv.lock",
    "system1.sh",
    "system1.ps1",
    ".env.example",
    ".gitignore",
    ".gitattributes",
    ".clang-format",
    ".python-version",
}
ROOT_DIRS = {"src", "native", "tests", "scripts", "configs", "docs", "standards", ".github"}
IGNORED = {".git", ".local", ".native-build", ".uv-cache", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def maintained_files(root: Path = ROOT) -> list[Path]:
    result = []
    for directory, names, files in os.walk(root):
        names[:] = sorted(
            n for n in names if n not in IGNORED and not n.startswith(".venv") and not n.endswith(".egg-info")
        )
        result.extend(Path(directory) / name for name in sorted(files) if not name.endswith(".pyc"))
    return sorted(result)


def root_errors(root: Path = ROOT) -> list[str]:
    errors = []
    for path in root.iterdir():
        if path.name in IGNORED or path.name.startswith(".venv"):
            continue
        if path.is_dir() and path.name not in ROOT_DIRS:
            errors.append(f"{path.name}: unowned root directory")
        elif path.is_file() and path.name not in ROOT_FILES:
            errors.append(f"{path.name}: unowned root file")
    return sorted(errors)
