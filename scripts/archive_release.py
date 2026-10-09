"""Build an immutable product archive from the verified tag, with source identity."""

import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

from layout import ROOT


def git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=ROOT, text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="annotated verified release tag at the clean current commit")
    args = parser.parse_args()
    if git("status", "--porcelain"):
        raise SystemExit("commit project changes before archiving")
    if git("cat-file", "-t", args.tag) != "tag" or git("rev-parse", args.tag + "^{commit}") != git("rev-parse", "HEAD"):
        raise SystemExit("release must be an annotated tag at the current verified commit")
    products = ROOT / ".local/products"
    products.mkdir(parents=True, exist_ok=True)
    destination = products / args.tag
    if destination.exists():
        raise SystemExit("product already exists; refusing to overwrite")
    with TemporaryDirectory(prefix="source-", dir=products) as directory:
        staging = Path(directory)
        archive_path = staging / "source.tar"
        with archive_path.open("wb") as stream:
            subprocess.run(["git", "archive", "--format=tar", args.tag], cwd=ROOT, stdout=stream, check=True)
        with tarfile.open(archive_path) as archive:
            archive.extractall(staging / "checkout", filter="data")
        subprocess.run(
            [
                "uv",
                "build",
                "--directory",
                str(staging / "checkout"),
                "--no-build-isolation",
                "--out-dir",
                str(destination),
            ],
            check=True,
        )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/artifact_check.py"), "--directory", str(destination)], check=True
    )
    files = {}
    for path in sorted(destination.iterdir()):
        with path.open("rb") as stream:
            files[path.name] = hashlib.file_digest(stream, "sha256").hexdigest()
    manifest = {"source_tag": args.tag, "source_commit": git("rev-parse", "HEAD"), "sha256": files}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
