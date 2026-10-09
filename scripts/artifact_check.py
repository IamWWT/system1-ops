"""Verify distributable assets and reject private runtime data in built archives."""

import argparse
import hashlib
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / ".local/dist")
    directory = parser.parse_args().directory
    artifacts = sorted(directory.glob("system1_ops-*.whl")) + sorted(directory.glob("system1_ops-*.tar.gz"))
    if len(artifacts) != 2:
        raise ValueError("expected one versioned wheel and one source archive")
    for path in artifacts:
        if path.suffix == ".whl":
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                if "system1_ops/web/index.html" not in names or "system1_ops/web/app.js" not in names:
                    raise ValueError("wheel lacks web assets")
        else:
            with tarfile.open(path) as archive:
                names = archive.getnames()
        for name in names:
            parts = Path(name).parts
            if any(
                part
                in (
                    ".local",
                    "config.toml",
                    ".env",
                    "models",
                    "vendor",
                    "logs",
                    "run",
                    "evidence",
                    ".venv",
                    ".venv-cu130",
                )
                for part in parts
            ):
                raise ValueError("private runtime data in artifact: " + name)
            if name.endswith((".gguf", ".safetensors")):
                raise ValueError("model weights in artifact")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        print(path.name + " SHA256=" + digest)
    print("PASS distributable assets and privacy checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
