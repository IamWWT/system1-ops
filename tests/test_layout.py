"""Directory ownership, isolation and portable runtime selection regressions."""

import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.layout import maintained_files, root_errors


def test_runtime_and_unknown_root_files_are_distinguished():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / ".local/logs").mkdir(parents=True)
        (root / ".local/logs/private.log").write_text("private")
        (root / "src").mkdir()
        (root / "src/main.py").write_text("pass")
        (root / "scratch.txt").write_text("unowned")
        assert root_errors(root) == ["scratch.txt: unowned root file"]
        assert [p.relative_to(root).as_posix() for p in maintained_files(root)] == ["scratch.txt", "src/main.py"]


def test_external_state_directory_and_legacy_configuration_selection():
    project = Path(__file__).resolve().parents[1]
    code = "import json; from system1_ops.common import STATE, DEFAULT_CONFIG; print(json.dumps([str(STATE),str(DEFAULT_CONFIG)]))"
    with TemporaryDirectory() as directory:
        root = Path(directory)
        state = root / "external"
        state.mkdir()
        (root / "config.toml").write_text("legacy")
        env = dict(os.environ, SYSTEM1_HOME=str(root), SYSTEM1_STATE_DIR=str(state), PYTHONPATH=str(project / "src"))

        def selected():
            result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)

        assert selected() == [str(state), str(root / "config.toml")]
        (state / "config.toml").write_text("current")
        assert selected() == [str(state), str(state / "config.toml")]
