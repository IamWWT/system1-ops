"""Portable lifecycle ownership, benchmark gates and dashboard controls."""

import asyncio
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import httpx

from system1_ops.benchmark import compatibility, fixtures
from system1_ops.common import DEFAULT_CONFIG, ROOT, config, preflight
from system1_ops.dashboard import create_dashboard
from system1_ops.portable import file_lock, identity, snapshot, tail
from system1_ops.startlux_policy import cpu_dtype


class Portable(unittest.TestCase):
    def test_port_probe_rejects_listener(self):
        import socket

        from system1_ops.portable import probe_port

        with socket.socket() as server:
            server.bind(("127.0.0.1", 0))
            server.listen()
            with self.assertRaises(OSError):
                probe_port("127.0.0.1", server.getsockname()[1])

    @unittest.skipIf(os.name == "nt", "POSIX TIME_WAIT reuse")
    def test_port_probe_permits_closed_server_time_wait(self):
        import socket

        from system1_ops.portable import probe_port

        with socket.socket() as server, socket.socket() as client:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", 0))
            port = server.getsockname()[1]
            server.listen()
            client.connect(("127.0.0.1", port))
            peer, _ = server.accept()
            peer.close()
            self.assertEqual(client.recv(1), b"")
        with socket.socket() as plain:
            with self.assertRaises(OSError):
                plain.bind(("127.0.0.1", port))
        probe_port("127.0.0.1", port)

    def test_bootstrap_fresh_checkout_and_preserves_local_changes(self):
        from system1_ops import bootstrap

        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            upstream = root / "origin"
            upstream.mkdir()

            def git(*args):
                return subprocess.run(
                    ["git", "-C", str(upstream), *args], check=True, capture_output=True, text=True
                ).stdout.strip()

            git("init", "-b", "main")
            (upstream / "file").write_text("first", encoding="utf-8")
            git("add", "file")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "initial")
            first = git("rev-parse", "HEAD")
            with (
                patch.object(bootstrap, "ROOT", root / "project"),
                patch.dict(bootstrap.SOURCES, {"fixture": (str(upstream), first)}),
            ):
                checkout = bootstrap.source("fixture")
                self.assertEqual((checkout / "file").read_text(encoding="utf-8"), "first")
                (checkout / "file").write_text("local change", encoding="utf-8")
                (upstream / "file").write_text("second", encoding="utf-8")
                git("add", "file")
                git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "second")
                bootstrap.SOURCES["fixture"] = (str(upstream), git("rev-parse", "HEAD"))
                with self.assertRaisesRegex(RuntimeError, "local edits"):
                    bootstrap.source("fixture")
                self.assertEqual((checkout / "file").read_text(encoding="utf-8"), "local change")

    def test_identity_live_and_dead(self):
        self.assertIsNotNone(identity(os.getpid()))
        self.assertIsNone(identity(2147483647))

    def test_atomic_snapshot_lock_and_tail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            with file_lock(root / "state.lock"):
                snapshot(root / "state.json", {"model": "中文"})
            self.assertEqual(json.loads((root / "state.json").read_text(encoding="utf-8"))["model"], "中文")
            (root / "log").write_text("a\nb\nc\n", encoding="utf-8")
            self.assertEqual(tail(root / "log", 2), "b\nc")

    def test_stale_pid_record_not_owned(self):
        from system1_ops import manage

        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "model.json").write_text(json.dumps({"pid": os.getpid(), "starttime": 0}))
            with patch.object(manage, "RUN", root):
                self.assertIsNone(manage.record("model"))

    def test_native_context_guard_and_complete_checkpoint(self):
        item = config(DEFAULT_CONFIG)["startlux-0.8b"]
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for name in ("decision_config.json", "tokenizer.json", "weights.safetensors"):
                (root / name).write_text("{}")
            (root / "config.json").write_text(json.dumps({"text_config": {"max_position_embeddings": 4096}}))
            (root / "model.safetensors.index.json").write_text(
                json.dumps({"weight_map": {"weight": "weights.safetensors"}})
            )
            (root / "startlux_decision").mkdir()
            item.update(
                path=str(root), source=str(root), python=sys.executable, context_length=4096, startlux_backend="torch"
            )
            self.assertEqual(preflight(item), 4096)
            item["context_length"] = 8192
            with self.assertRaisesRegex(ValueError, "native limit"):
                preflight(item)

    def test_cpu_dtype_conservative_fallback(self):
        with patch("system1_ops.startlux_policy.cpu_flags", return_value=[]):
            self.assertEqual(cpu_dtype("auto"), "fp32")
        with patch("system1_ops.startlux_policy.cpu_flags", return_value=["amx_bf16"]):
            self.assertEqual(cpu_dtype("auto"), "bf16")

    def test_probability_and_choice_gate(self):
        expected = {
            "case": {
                "answers": {
                    "q": {"type": "choice", "choice": "a", "confidence": 0.4, "probabilities": {"a": 0.7, "b": 0.3}}
                }
            }
        }
        same = json.loads(json.dumps(expected))
        self.assertTrue(compatibility(expected, same)["passed"])
        same["case"]["answers"]["q"]["probabilities"]["a"] = 0.75
        self.assertFalse(compatibility(expected, same)["passed"])
        same = json.loads(json.dumps(expected))
        same["case"]["answers"]["q"]["choice"] = "b"
        self.assertFalse(compatibility(expected, same)["passed"])
        self.assertEqual(len(fixtures("quick")), 4)


class Dashboard(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async def heartbeat():
            while True:
                await asyncio.sleep(0.01)

        self.heartbeat = asyncio.create_task(heartbeat())

    async def asyncTearDown(self):
        if hasattr(self, "lifecycle"):
            await self.lifecycle.__aexit__(None, None, None)
        self.heartbeat.cancel()

    async def client(self, key="test-admin-key"):
        with patch.dict(os.environ, SYSTEM1_ADMIN_KEY=key):
            self.app = create_dashboard(DEFAULT_CONFIG)
        self.lifecycle = self.app.router.lifespan_context(self.app)
        await self.lifecycle.__aenter__()
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://local")

    async def test_page_and_read_only_mode(self):
        async with await self.client("") as client:
            page = await client.get("/")
            self.assertEqual(page.status_code, 200)
            self.assertIn("运维台", page.text)
            self.assertEqual((await client.get("/app.js")).status_code, 200)
            denied = await client.post("/ops/models/laya/start")
            self.assertEqual(denied.status_code, 403)

    async def test_auth_and_debug_whitelist(self):
        async with await self.client() as client:
            self.assertEqual((await client.get("/ops/reports")).status_code, 401)
            headers = {"Authorization": "Bearer test-admin-key"}
            self.assertEqual((await client.post("/ops/models/not-a-model/start", headers=headers)).status_code, 404)
            self.assertEqual(
                (await client.post("/ops/debug/laya", content="invalid", headers=headers)).status_code, 400
            )
            self.assertEqual(
                (await client.post("/ops/debug/laya", content="x" * (1024 * 1024 + 1), headers=headers)).status_code,
                413,
            )

    async def test_async_operation_and_failure_report(self):
        async with await self.client() as client:
            headers = {"Authorization": "Bearer test-admin-key"}
            with patch("system1_ops.dashboard.start", side_effect=RuntimeError("missing checkpoint")):
                job = await client.post("/ops/models/laya/start", headers=headers)
                self.assertEqual(job.status_code, 202)
                for _ in range(50):
                    result = await client.get("/ops/jobs/" + job.json()["id"], headers=headers)
                    if result.json()["status"] != "running":
                        break
                    await asyncio.sleep(0.01)
                self.assertEqual(result.json()["status"], "failed")
                self.assertIn("missing checkpoint", result.json()["error"])

    async def test_source_has_no_html_injection(self):
        source = (ROOT / "src" / "system1_ops" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", source)
        self.assertNotIn("localStorage", source)


if __name__ == "__main__":
    unittest.main()
