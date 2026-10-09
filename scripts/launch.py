"""Launch a package module with the selected Python environment."""

import runpy
import sys
from pathlib import Path

MODULES = {"manage", "worker", "dashboard", "bootstrap", "benchmark", "publish", "verify_native", "verify_real"}


def main(module: str | None = None) -> None:
    if module is None:
        if len(sys.argv) < 2 or sys.argv[1] not in MODULES:
            raise SystemExit("usage: launch.py " + "|".join(sorted(MODULES)) + " [arguments]")
        module = sys.argv.pop(1)
    if module not in MODULES:
        raise SystemExit("unknown command module")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    runpy.run_module("system1_ops." + module, run_name="__main__")


if __name__ == "__main__":
    main()
