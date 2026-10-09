"""Explicitly regenerate navigation for every maintained file (never runtime data)."""

import argparse
from pathlib import Path

try:
    from .layout import ROOT, maintained_files
except ImportError:
    from layout import ROOT, maintained_files


def header(title: str) -> str:
    return f"""---
title: {title}
type: index
status: active
version: 0.3.0
date: 2026-10-09
owner: IamWWT
applies_to: System1 Ops
references:
  - docs/FILE_INDEX.md
---

# {title}

> 关联: [[FILE_INDEX|全库文件索引]]
"""


def write_indexes(root: Path = ROOT) -> None:
    directories = {p.parent for p in maintained_files(root) if p.suffix == ".md" and p.is_relative_to(root / "docs")}
    # Public test sample directories also have navigation.
    directories.add(root / "docs/05-testing/samples")
    for directory in sorted(directories):
        if directory == root / "docs":
            continue
        relative = directory.relative_to(root / "docs").as_posix()
        contents = [header(relative + " 导航")]
        for p in sorted(directory.iterdir()):
            if p.name == "index.md":
                continue
            if p.is_dir():
                target = p / "index.md"
                if target.exists():
                    contents.append(f"- [[{target.relative_to(root / 'docs').with_suffix('').as_posix()}|{p.name}]]")
            elif p.suffix == ".md":
                contents.append(f"- [[{p.relative_to(root / 'docs').with_suffix('').as_posix()}|{p.name}]]")
            else:
                contents.append(f"- [{p.name}]({p.name})")
        (directory / "index.md").write_text("\n\n".join(contents) + "\n", encoding="utf-8")
    contents = [header("全库文件索引")]
    for p in maintained_files(root):
        relative = p.relative_to(root).as_posix()
        if p.is_relative_to(root / "docs") and p.suffix == ".md":
            contents.append(f"- [[{p.relative_to(root / 'docs').with_suffix('').as_posix()}|{relative}]]")
        else:
            contents.append(f"- [{relative}](../{relative})")
    (root / "docs/FILE_INDEX.md").write_text("\n".join(contents) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", required=True, help="explicitly replace navigation only")
    parser.parse_args()
    write_indexes()


if __name__ == "__main__":
    main()
