"""Cross-platform documentation gate; scans maintained files, not model caches."""

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    ".git",
    "vendor",
    "models",
    "reports",
    "evidence",
    "logs",
    "run",
    "dist",
    ".native-build",
    ".uv-cache",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


def markdown_files(root: Path) -> list[Path]:
    result = []
    for directory, names, files in os.walk(root):
        names[:] = [n for n in names if n not in EXCLUDED and not n.startswith(".venv") and not n.endswith(".egg-info")]
        result.extend(Path(directory) / name for name in files if name.endswith(".md"))
    return sorted(result)


def prose(text: str) -> str:
    text = re.sub(r"(?ms)^```.*?^```[^\n]*", "", text)
    return re.sub(r"`[^`\n]*`", "", text)


def resolve(root: Path, source: Path, target: str, wiki: bool) -> Path | None:
    target = target.replace("\\|", "|").split("|")[0].split("#")[0]
    if not target or re.match(r"^(https?://|mailto:|app://)", target):
        return None
    if wiki and not target.endswith(".md"):
        target += ".md"
    candidates = [root / "docs" / target, source.parent / target, root / target] if wiki else [source.parent / target]
    return next((p for p in candidates if p.exists()), candidates[0])


def check(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    files = markdown_files(root)
    index = root / "docs/FILE_INDEX.md"
    listing = index.read_text(encoding="utf-8") if index.exists() else ""
    if not listing:
        errors.append("missing docs/FILE_INDEX.md")
    manifest_path = root / "standards/source.json"
    manifest: dict[str, Any] = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"files": {}}
    for p in files:
        relative = p.relative_to(root).as_posix()
        text = p.read_text(encoding="utf-8")
        if relative != "docs/FILE_INDEX.md" and relative not in listing:
            errors.append(f"{relative}: not registered in FILE_INDEX")
        if relative.startswith("standards/"):
            source_key = p.relative_to(root / "standards").as_posix()
            if hashlib.sha256(p.read_bytes()).hexdigest() != manifest["files"].get(source_key):
                errors.append(f"{relative}: imported standard differs from source manifest")
            # Imported standards are preserved verbatim, including their template examples.
            continue
        body = prose(text)
        is_journal = bool(re.match(r"\d{4}-\d{2}-\d{2}", p.stem)) or p.name in (
            "CHANGELOG.md",
            "AGENTS.md",
            "MEMORY.md",
        )
        if not is_journal:
            match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
            if not match:
                errors.append(f"{relative}: missing frontmatter")
            else:
                data = yaml.safe_load(match[1])
                for field in ("title", "type", "status", "version", "date", "owner"):
                    if field not in data:
                        errors.append(f"{relative}: missing {field}")
                heading = re.search(r"^# (.+)$", text, re.M)
                if not heading or data.get("title") != heading[1]:
                    errors.append(f"{relative}: title differs from H1")
        if len(re.findall(r"^# ", body, re.M)) != 1:
            errors.append(f"{relative}: expected one H1")
        if "{{" in body:
            errors.append(f"{relative}: unresolved template variable")
        if "\r" in text or re.search(r" +$", text, re.M):
            errors.append(f"{relative}: trailing whitespace/CRLF")
        for target in re.findall(r"\[\[([^\]]+)\]\]", body):
            dest = resolve(root, p, target, True)
            if dest is not None and not dest.exists():
                errors.append(f"{relative}: broken wikilink {target}")
        for target in re.findall(r"(?<!!)\[[^\]\n]*\]\(([^)]+)\)", body):
            dest = resolve(root, p, target, False)
            if dest is not None and not dest.exists():
                errors.append(f"{relative}: broken link {target}")
    for directory in sorted({p.parent for p in files if "docs" in p.relative_to(root).parts}):
        navigation = directory / "index.md"
        if not navigation.exists():
            navigation = directory / "README.md"
        if not navigation.exists():
            errors.append(f"{directory.relative_to(root)}: missing navigation")
            continue
        nav = navigation.read_text(encoding="utf-8")
        for p in directory.glob("*.md"):
            if p != navigation and p.name not in nav and p.stem not in nav:
                errors.append(f"{navigation.relative_to(root)}: missing navigation for {p.name}")
    return errors


def main() -> int:
    errors = check()
    print("\n".join(errors) if errors else "PASS: frontmatter, indexes, links, placeholders and imported standards")
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
