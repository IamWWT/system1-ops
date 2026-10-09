"""ASGI contract and resource admission checks; no sockets or checkpoints required."""
import asyncio
import json
import os
import threading
import time
import unittest
from unittest.mock import patch

import httpx

from common import DEFAULT_CONFIG, config, preflight
from worker import Engine, choose_device, create_app, project_jev


class FakeEngine:
    def __init__(self):
        self.lock = threading.Lock()
        self.model = object()
        self.device = "cpu"
        self.reason = "test"
        self.loaded_at = time.time()
        self.last_used = time.monotonic()
        self.delay = 0
        self.entered = threading.Event()

    def infer(self, body, request_id):
        try:
            self.entered.set()
            time.sleep(self.delay)
            if body["state"] == "invalid":
                raise ValueError("context limit")
            return {"model": "laya", "answers": {"q": {"type": "noul", "noul": 0.9}},
                    "usage": {"input_tokens": 1, "output_tokens": 1}}
        finally:
            self.lock.release()

    def unload(self):
        self.model = None


class API(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Some restricted sandboxes block asyncio's cross-thread wakeup socket.
        async def heartbeat():
            while True:
                await asyncio.sleep(0.01)
        self.heartbeat = asyncio.create_task(heartbeat())
        self.item = config(DEFAULT_CONFIG)["laya"]
        self.engine = FakeEngine()
        self.app = create_app(self.item, self.engine)
        self.lifecycle = self.app.router.lifespan_context(self.app)
        await self.lifecycle.__aenter__()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://local")
        self.body = {"state": "hello", "questions": {"q": {"type": "noul", "instructions": "True?"}}}

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.lifecycle.__aexit__(None, None, None)
        self.heartbeat.cancel()

    async def test_contract(self):
        response = await self.client.post("/v1/systemone", json=self.body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"model", "answers", "usage"})
        self.assertTrue(response.headers["x-typesafe-request-id"])
        self.assertEqual((await self.client.get("/health")).json()["device"], "cpu")

    async def test_bad_body_and_limit(self):
        for payload in ([], {}, {"state": "x", "questions": []}):
            self.assertEqual((await self.client.post("/v1/systemone", json=payload)).status_code, 400)
        self.item["max_body_bytes"] = 10
        self.assertEqual((await self.client.post("/v1/systemone", json=self.body)).status_code, 413)

    async def test_model_validation(self):
        body = dict(self.body, state="invalid")
        self.assertEqual((await self.client.post("/v1/systemone", json=body)).status_code, 422)
        self.assertFalse(self.engine.lock.locked())

    async def test_busy_does_not_queue_inference(self):
        self.engine.delay = 0.15
        first = asyncio.create_task(self.client.post("/v1/systemone", json=self.body))
        while not self.engine.entered.is_set():
            await asyncio.sleep(0.002)
        self.assertEqual((await self.client.post("/v1/systemone", json=self.body)).status_code, 503)
        self.assertEqual((await self.client.get("/health")).status_code, 200)
        self.assertEqual((await first).status_code, 200)

    async def test_timeout_keeps_inference_lock(self):
        self.item["inference_timeout"] = 0.02
        self.engine.delay = 0.15
        self.assertEqual((await self.client.post("/v1/systemone", json=self.body)).status_code, 504)
        self.assertTrue(self.engine.lock.locked())
        self.assertEqual((await self.client.post("/v1/systemone", json=self.body)).status_code, 503)
        await asyncio.sleep(0.2)
        self.assertFalse(self.engine.lock.locked())

    async def test_auth(self):
        with patch.dict(os.environ, SYSTEM1_API_KEY="test-only-key"):
            app = create_app(self.item, self.engine)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://local") as client:
                self.assertEqual((await client.post("/v1/systemone", json=self.body)).status_code, 401)
                self.assertEqual((await client.get("/health")).status_code, 200)
                self.assertEqual((await client.post("/v1/systemone", json=self.body,
                                                  headers={"Authorization": "Bearer test-only-key"})).status_code, 200)

    async def test_idle_unload(self):
        item = dict(self.item, idle_unload_seconds=0.01)
        engine = FakeEngine()
        engine.last_used -= 1
        app = create_app(item, engine)
        async with app.router.lifespan_context(app):
            deadline = asyncio.get_running_loop().time() + 2
            while engine.model is not None or engine.lock.locked():
                if asyncio.get_running_loop().time() >= deadline:
                    break
                await asyncio.sleep(0.01)
            self.assertIsNone(engine.model)
            self.assertFalse(engine.lock.locked())


class Preflight(unittest.TestCase):
    def test_real_checkpoint_completeness(self):
        items = config(DEFAULT_CONFIG)
        if not os.path.exists(items["laya"]["path"]) or not os.path.exists(items["startlux-0.8b"]["path"]):
            self.skipTest("local checkpoint integration check; CI does not download weights")
        self.assertEqual(preflight(items["laya"]), 8192)
        self.assertEqual(preflight(items["startlux-0.8b"]), 262144)

    def test_missing_shard(self):
        import tempfile
        import pathlib
        item = config(DEFAULT_CONFIG)["startlux-4b"]
        with tempfile.TemporaryDirectory() as directory:
            item["path"] = directory
            pathlib.Path(directory, "model.safetensors.index.json").write_text(
                json.dumps({"weight_map": {"weight": "missing.safetensors"}}))
            with self.assertRaisesRegex(ValueError, "missing.safetensors"):
                preflight(item)

    def test_auto_cpu_and_explicit_gpu_failure(self):
        from types import SimpleNamespace
        torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
        item = config(DEFAULT_CONFIG)["laya"]
        self.assertEqual(choose_device(item, torch)[0], "cpu")
        item["device"] = "cuda:0"
        with self.assertRaisesRegex(RuntimeError, "Explicit device"):
            choose_device(item, torch)

    def test_gpu_reserve(self):
        from types import SimpleNamespace
        torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: True,
                                                     mem_get_info=lambda index: (1024**3, 24 * 1024**3)))
        item = config(DEFAULT_CONFIG)["laya"]
        self.assertEqual(choose_device(item, torch)[0], "cpu")

    def test_strict_projection(self):
        raw = {"model": "test", "routing": {}, "answers": {"q": {"type": "noul", "noul": 0.5,
                                                                      "action": {}, "confidence": 0.5}},
               "usage": {"input_tokens": 3, "output_tokens": 1, "windows": 2}}
        self.assertEqual(project_jev(raw)["answers"]["q"], {"type": "noul", "noul": 0.5})
        self.assertNotIn("windows", project_jev(raw)["usage"])

    def test_infer_failure_releases_lock(self):
        engine = Engine(config(DEFAULT_CONFIG)["laya"])
        engine.lock.acquire()
        with patch.object(engine, "load", side_effect=RuntimeError("failed")):
            with self.assertRaises(RuntimeError):
                engine.infer({}, "test")
        self.assertFalse(engine.lock.locked())

    def test_native_auto_failure_retries_cpu_but_forced_cuda_does_not(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        body = {"state": "x", "questions": {"q": {"type": "noul", "instructions": "True?"}}}
        for device in ("auto", "cuda:0"):
            item = dict(config(DEFAULT_CONFIG)["startlux-0.8b"], device=device, startlux_backend="gguf-stdio")
            engine = Engine(item)
            engine.device = "cuda:0"
            engine.model = SimpleNamespace(decide=Mock(side_effect=RuntimeError("native decode failed")))
            cpu_model = SimpleNamespace(decide=Mock(return_value=({"q": {"type": "noul", "noul": 0.8}},
                                                                 {"input_tokens": 1, "output_tokens": 0})))

            def load_cpu():
                self.assertEqual(engine.device, "cpu")
                self.assertEqual(item["llama_gpu_layers"], 0)
                engine.model = cpu_model

            engine.lock.acquire()
            with patch.object(engine, "load"), patch.object(engine, "unload"), patch.object(engine, "_load_model", side_effect=load_cpu):
                if device == "auto":
                    self.assertEqual(engine.infer(body, "native-fallback")["answers"]["q"]["noul"], 0.8)
                else:
                    with self.assertRaisesRegex(RuntimeError, "native decode failed"):
                        engine.infer(body, "native-forced-cuda")
                    cpu_model.decide.assert_not_called()
            self.assertFalse(engine.lock.locked())


if __name__ == "__main__":
    unittest.main()
