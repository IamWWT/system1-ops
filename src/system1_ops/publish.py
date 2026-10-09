"""Publish this committed project to the user-authorized public IamWWT repository."""

import subprocess
import sys
from typing import Any

from .common import ROOT


def run(*args: Any, capture: Any = False) -> Any:
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=capture)
    if result.returncode and capture:
        print(result.stderr, file=sys.stderr, end="")
    result.check_returncode()
    return result


def main() -> Any:
    owner = run("gh", "api", "user", "--jq", ".login", capture=True).stdout.strip()
    if owner != "IamWWT":
        raise RuntimeError("gh must be authenticated as IamWWT")
    if run("git", "status", "--porcelain", capture=True).stdout.strip():
        raise RuntimeError("commit tracked project changes before publishing")
    repo = "IamWWT/system1-ops"
    view = subprocess.run(["gh", "repo", "view", repo, "--json", "nameWithOwner"], cwd=ROOT, capture_output=True)
    if view.returncode:
        run(
            "gh",
            "repo",
            "create",
            repo,
            "--public",
            "--description",
            "Portable Jev decision inference operations: Laya, StartLux, C++ llama.cpp, FastAPI and dashboard",
        )
    remotes = run("git", "remote", capture=True).stdout.splitlines()
    url = "https://github.com/" + repo + ".git"
    if "origin" not in remotes:
        run("git", "remote", "add", "origin", url)
    elif run("git", "remote", "get-url", "origin", capture=True).stdout.strip() != url:
        raise RuntimeError("existing origin differs; refusing to replace it")
    run("git", "push", "-u", "origin", "main")


if __name__ == "__main__":
    main()
