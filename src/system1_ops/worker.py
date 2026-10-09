"""Single-model FastAPI worker, running in the model's own Python runtime."""

import argparse
import asyncio
import gc
import hmac
import json
import logging
import os
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Any

from .common import ROOT, add_overrides, apply_overrides, config, load_local_environment, preflight, prepare_runtime
from .logging_config import configure_logging
from .portable import snapshot

LOG = logging.getLogger("system1")


class LogStream:
    """Capture dependency prints/progress and tracebacks in the rotated log too."""

    def __init__(self, level: Any) -> None:
        self.level = level
        self.buffer = ""
        self.encoding = "utf-8"

    def write(self, value: Any) -> Any:
        self.buffer += value.replace("\r", "\n")
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line.strip():
                LOG.log(self.level, "%s", line)
        return len(value)

    def flush(self) -> Any:
        if self.buffer.strip():
            LOG.log(self.level, "%s", self.buffer)
        self.buffer = ""

    def isatty(self) -> Any:
        return False


def project_jev(result: Any) -> Any:
    fields = {
        "choice": ("type", "choice", "probabilities", "confidence"),
        "score": ("type", "score", "probabilities", "confidence", "legend"),
        "noul": ("type", "noul"),
    }
    return {
        "model": result["model"],
        "answers": {key: {f: answer[f] for f in fields[answer["type"]]} for key, answer in result["answers"].items()},
        "usage": {key: result["usage"].get(key, 0) for key in ("input_tokens", "output_tokens")},
    }


def choose_device(item: Any, torch: Any) -> Any:
    requested = item["device"]
    if requested == "cpu":
        return "cpu", "CPU explicitly configured"
    index = item["gpu_index"] if requested == "auto" else int(requested.split(":")[1])
    reason = "CUDA unavailable in this Python runtime"
    if torch.cuda.is_available():
        try:
            free, total = torch.cuda.mem_get_info(index)
            needed = (item["gpu_required_mb"] + item["gpu_reserve_mb"]) * 1024**2
            reason = f"GPU {index}: free={free // 1024**2}MB total={total // 1024**2}MB required+reserve={needed // 1024**2}MB"
            if free >= needed:
                if item["kind"] == "startlux" and not item["allow_slow_cuda"]:
                    from startlux_decision.model import fast_kernels_active

                    if not fast_kernels_active(item["path"]):
                        reason += "; StartLux fast CUDA kernels unavailable"
                    else:
                        return f"cuda:{index}", reason
                else:
                    return f"cuda:{index}", reason
        except (RuntimeError, ValueError) as error:
            reason = f"CUDA probe failed: {error}"
    if requested != "auto":
        raise RuntimeError(f"Explicit device {requested} cannot be used: {reason}")
    return "cpu", reason


class Engine:
    def __init__(self, item: Any) -> None:
        self.item = item
        self.model: Any = None
        self.device: str | None = None
        self.reason: str | None = None
        self.loaded_at: float | None = None
        self.last_used = time.monotonic()
        self.lock = threading.Lock()
        self.metrics: dict[str, Any] = {"requests": 0, "errors": 0, "last_latency_ms": None, "last_usage": None}
        self.precision: str | None = None
        self.backend = "eager"
        self.native_process: Any = None

    def load(self) -> Any:
        if self.model is not None:
            return
        import torch

        if self.item["cpu_affinity"]:
            import psutil

            psutil.Process().cpu_affinity(self.item["cpu_affinity"])
        torch.set_num_threads(self.item["threads"])
        if self.device is None:
            torch.set_num_interop_threads(self.item.get("torch_interop_threads", 1))
        if self.item.get("startlux_backend", "torch").startswith("gguf"):
            self.device = "cpu"
            self.reason = "C++ GGUF CPU backend"
            if self.item["device"] != "cpu":
                from .portable import hardware

                index = (
                    int(self.item["device"].split(":")[1])
                    if self.item["device"].startswith("cuda:")
                    else self.item["gpu_index"]
                )
                gpu = next((g for g in hardware()["gpus"] if g["index"] == index), None)
                budget = self.item["gpu_required_mb"] + self.item["gpu_reserve_mb"]
                if gpu and gpu["free_mb"] >= budget:
                    self.device = f"cuda:{index}"
                    self.reason = "native GPU offload requested; verify layer placement in native log"
                    self.item["llama_gpu_layers"] = self.item["llama_gpu_layers"] or -1
                    os.environ["CUDA_VISIBLE_DEVICES"] = str(index)
                elif self.item["device"] != "auto":
                    raise RuntimeError("native CUDA device unavailable or free VRAM below configured budget")
                else:
                    self.reason = (self.reason or "") + "; GPU unavailable or below configured VRAM budget"
            if self.device == "cpu":
                self.item["llama_gpu_layers"] = 0
        else:
            self.device, self.reason = choose_device(self.item, torch)
        LOG.info("device_selection requested=%s actual=%s reason=%s", self.item["device"], self.device, self.reason)
        started = time.monotonic()
        try:
            self._load_model()
        except (RuntimeError, MemoryError) as error:
            # Retry only an automatic CUDA selection, and only memory failures.
            recoverable = "memory" in str(error).lower() or (
                self.item.get("startlux_backend", "torch").startswith("gguf") and "no GPU backend" in str(error)
            )
            if self.item["device"] != "auto" or not (self.device or "").startswith("cuda") or not recoverable:
                raise
            LOG.exception("GPU model load exhausted memory; retrying CPU")
            error.__traceback__ = None
            gc.collect()
            torch.cuda.empty_cache()
            self.device = "cpu"
            self.reason = "CUDA allocation / backend unavailable; CPU fallback"
            self.item["llama_gpu_layers"] = 0
            self._load_model()
        actual = getattr(self.model, "device", self.device)
        self.device = str(actual)
        self.loaded_at = time.time()
        LOG.info(
            "model_loaded model=%s device=%s seconds=%.3f", self.item["name"], self.device, time.monotonic() - started
        )

    def _load_model(self) -> Any:
        assert self.device is not None
        a = self.item
        if a["kind"] == "laya":
            import torch
            from laya import load

            from .startlux_policy import cpu_dtype

            os.environ["LAYA_CPU_AMP"] = "bf16" if cpu_dtype(a["cpu_dtype"]) == "bf16" else ""
            self.model = load(a["path"], device=self.device, backend="eager")
            if self.device.startswith("cuda"):
                selected = {"fp32": torch.float32, "bf16": torch.bfloat16, "fp16": torch.float16}[a["laya_gpu_dtype"]]
                self.model.dtype = selected
                self.model.amp_enabled = selected != torch.float32
                torch.backends.cuda.matmul.allow_tf32 = a["laya_gpu_tf32"]
                torch.backends.cudnn.allow_tf32 = a["laya_gpu_tf32"]
            self.model.model.encoder.config._attn_implementation = a["attention"]
            if self.device == "cpu" and a.get("cpu_quantization") == "int8":
                self.model.model.encoder = torch.ao.quantization.quantize_dynamic(
                    self.model.model.encoder, {torch.nn.Linear}, dtype=torch.qint8, inplace=True
                )
                self.precision = "int8-encoder/fp32-head"
            else:
                self.precision = str(self.model.dtype)
            if a.get("laya_backend", "eager") != "eager":
                from laya.backends import install

                backend = install(self.model, a["laya_backend"], strict=not a.get("fallback_eager", True))
                self.backend = getattr(backend, "name", type(backend).__name__)
            self.model.cfg["head_max_len"] = a["head_max_length"]
            self.model.cfg["max_len"] = a["window_length"] if a["long_input"] == "window" else a["context_length"]
        else:
            if a.get("startlux_backend", "torch").startswith("gguf"):
                from .native_gguf import load

                self.model, self.native_process = load(a)
                self.backend = "llama.cpp"
                self.precision = "GGUF (see model filename)"
                return
            from .startlux_policy import apply, cpu_dtype

            self.precision = cpu_dtype(a.get("cpu_dtype", "auto")) if self.device == "cpu" else "bf16"
            apply(self.precision, a["attention"])
            from startlux_decision.model import StartLuxDecision

            self.model = StartLuxDecision(
                a["path"],
                device=self.device,
                max_length=a["context_length"],
                max_batch_tokens=a["max_batch_tokens"],
                graphs=a["cuda_graphs"],
                prefill_chunk=a["prefill_chunk"],
                images=a["images"],
            )
        LOG.info(
            "inference_policy precision=%s backend=%s threads=%s affinity=%s",
            self.precision,
            self.backend,
            a["threads"],
            a.get("cpu_affinity", []),
        )

    def unload(self) -> Any:
        if self.native_process is not None:
            from .native_gguf import stop_process

            stop_process(self.native_process)
            self.native_process = None
            if hasattr(self.model, "pool"):
                self.model.pool.shutdown(wait=True)
        self.model = None
        gc.collect()
        import torch

        if self.device and self.device.startswith("cuda"):
            torch.cuda.empty_cache()
        elif sys.platform == "linux":
            # Return freed CPU allocations where glibc otherwise retains its arenas.
            import ctypes

            try:
                ctypes.CDLL(None).malloc_trim(0)
            except AttributeError:
                pass
        LOG.info("model_unloaded model=%s idle_seconds=%s", self.item["name"], self.item["idle_unload_seconds"])

    def infer(self, body: Any, request_id: Any) -> Any:
        if self.item.get("serialize_inference"):
            from .portable import file_lock

            entered = False
            try:
                with file_lock(ROOT / "run" / "inference.lock"):
                    entered = True
                    return self._infer(body, request_id)
            finally:
                if not entered:
                    self.lock.release()
        return self._infer(body, request_id)

    def _infer(self, body: Any, request_id: Any) -> Any:
        start = time.monotonic()
        try:
            self.load()
            assert self.device is not None
            a = self.item
            state, questions = body["state"], body["questions"]
            budget = body.get("max_len", a["context_length"])
            if type(budget) is not int or not 256 <= budget <= a["context_length"]:
                raise ValueError(f"max_len must be 256..{a['context_length']}")
            if a["kind"] == "laya":
                text = state if isinstance(state, str) else json.dumps(state, ensure_ascii=False)
                tokens = len(self.model.tok.encode(text, add_special_tokens=False))
                if tokens > budget:
                    raise ValueError(f"state tokens {tokens} exceed limit {budget}")
                if a["long_input"] == "window":
                    # predict_long uses cfg.max_len; the effective window includes question heads.
                    self.model.cfg["max_len"] = min(a["window_length"], budget)
                    result = self.model.predict_long(state, questions, batch_size=1)
                    if result["usage"].get("truncated"):
                        raise ValueError("window inference truncated input; adjust window/head configuration")
                else:
                    result = self.model.predict(state, questions, max_len=budget, head_max_len=a["head_max_length"])
                    if result["usage"].get("truncated"):
                        raise ValueError("state plus question exceeds context; use long_input='window'")
            else:
                self.model.max_length = budget
                images = body.get("images")
                if images:
                    if not a["images"]:
                        raise ValueError("images disabled by configuration")
                    from startlux_decision.model import load_image

                    images = [load_image(value, paths=False) for value in images]
                try:
                    answers, usage = self.model.decide(state, questions, images=images)
                except (RuntimeError, OSError):
                    if (
                        a["device"] != "auto"
                        or not (self.device or "").startswith("cuda")
                        or not a.get("startlux_backend", "torch").startswith("gguf")
                    ):
                        raise
                    LOG.exception("native CUDA inference failed; retrying this request once on CPU")
                    self.unload()
                    self.device = "cpu"
                    self.reason = "native CUDA inference failure; CPU fallback"
                    a["llama_gpu_layers"] = 0
                    self._load_model()
                    self.loaded_at = time.time()
                    self.model.max_length = budget
                    answers, usage = self.model.decide(state, questions, images=images)
                result = {"answers": answers, "usage": usage}
            result["model"] = a["name"]
            self.metrics.update(
                requests=self.metrics["requests"] + 1,
                last_latency_ms=round(1000 * (time.monotonic() - start), 3),
                last_usage=result["usage"],
            )
            LOG.info(
                "inference_done request_id=%s model=%s device=%s seconds=%.3f questions=%s usage=%s",
                request_id,
                a["name"],
                self.device,
                time.monotonic() - start,
                len(questions),
                result["usage"],
            )
            if a["log_payloads"]:
                LOG.info("response request_id=%s payload=%s", request_id, json.dumps(result, ensure_ascii=False))
            return project_jev(result) if a["strict_jev"] else result
        except Exception:
            self.metrics["errors"] += 1
            LOG.exception("inference_failed request_id=%s seconds=%.3f", request_id, time.monotonic() - start)
            raise
        finally:
            try:
                if self.item.get("unload_after_request") and self.model is not None:
                    self.unload()
            finally:
                self.last_used = time.monotonic()
                self.lock.release()


def create_app(item: Any, engine: Any) -> Any:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="inference")
    key = os.environ.get(item["api_key_env"], "")

    def error(code: Any, message: Any) -> Any:
        return JSONResponse(
            {"error": message, "detail": [{"loc": ["body"], "msg": message, "type": "value_error"}]}, status_code=code
        )

    async def reaper() -> Any:
        while True:
            await asyncio.sleep(min(5, item["idle_unload_seconds"]))
            if engine.model is not None and time.monotonic() - engine.last_used >= item["idle_unload_seconds"]:
                if engine.lock.acquire(blocking=False):
                    try:
                        await asyncio.get_running_loop().run_in_executor(pool, engine.unload)
                    finally:
                        engine.lock.release()

    @asynccontextmanager
    async def lifespan(app: Any) -> Any:
        task = asyncio.create_task(reaper()) if item["idle_unload_seconds"] else None
        yield
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        pool.shutdown(wait=True)
        if engine.model is not None and hasattr(engine, "unload"):
            engine.unload()

    app = FastAPI(title="Local System 1 decision API", lifespan=lifespan)

    @app.middleware("http")
    async def access(request: Any, call_next: Any) -> Any:
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        start = time.monotonic()
        if (
            key
            and request.url.path not in ("/health", "/v1/health")
            and not hmac.compare_digest(request.headers.get("authorization", ""), "Bearer " + key)
        ):
            response = error(401, "unauthorized")
        else:
            response = await call_next(request)
        response.headers["x-typesafe-request-id"] = request_id
        response.headers["x-request-id"] = request_id
        LOG.info(
            "http request_id=%s client=%s method=%s path=%s status=%s seconds=%.3f",
            request_id,
            request.client.host if request.client else "",
            request.method,
            request.url.path,
            response.status_code,
            time.monotonic() - start,
        )
        return response

    @app.get("/health")
    @app.get("/v1/health")
    def health() -> Any:
        import psutil

        process = psutil.Process()
        rss = process.memory_info().rss
        for child in process.children(recursive=True):
            try:
                rss += child.memory_info().rss
            except psutil.NoSuchProcess:
                pass
        return {
            "status": "ok",
            "model": item["name"],
            "backend": "llama.cpp" if item.get("startlux_backend", "torch").startswith("gguf") else "torch",
            "loaded": engine.model is not None,
            "device": engine.device,
            "device_reason": engine.reason,
            "max_length": item["context_length"],
            "images": item["images"],
            "busy": engine.lock.locked(),
            "loaded_at": engine.loaded_at,
            "fast_kernels": getattr(engine.model, "fast_kernels", False),
            "cuda_graphs": len(getattr(engine.model, "graphs", {})),
            "rss_mb": round(rss / 1024**2, 1),
            "precision": getattr(engine, "precision", None),
            "inference_backend": getattr(engine, "backend", "eager"),
            "metrics": getattr(engine, "metrics", {}),
            "long_input": item.get("long_input", "native"),
        }

    @app.get("/v1/models")
    def models() -> Any:
        return {
            "models": [
                {"name": item["name"], "description": "Local typed decision model", "release_date": "2026-10-01"}
            ]
        }

    @app.post("/v1/systemone")
    async def systemone(request: Request) -> Any:
        chunks = bytearray()
        try:
            async for chunk in request.stream():
                if len(chunks) + len(chunk) > item["max_body_bytes"]:
                    return error(413, "request body exceeds configured byte limit")
                chunks.extend(chunk)
            body = json.loads(chunks)
            if not isinstance(body, dict) or body.get("state") is None:
                raise ValueError("body must be an object with state and questions")
            questions = body.get("questions")
            if not isinstance(questions, dict) or not 1 <= len(questions) <= item["max_questions"]:
                raise ValueError(f"questions must contain 1..{item['max_questions']} entries")
            for question in questions.values():
                if not isinstance(question, dict) or question.get("type") not in ("choice", "score", "noul"):
                    raise ValueError("question type must be choice, score or noul")
            images = body.get("images")
            if images and (not isinstance(images, list) or not all(isinstance(x, str) for x in images)):
                raise ValueError("images must be base64 strings")
            if images and item["kind"] == "laya":
                raise ValueError("Laya supports text only")
        except (ValueError, UnicodeDecodeError) as exc:
            return error(400, str(exc))
        if not engine.lock.acquire(blocking=False):
            return error(503, "model busy; retry later")
        request_id = request.state.request_id
        LOG.info("inference_start request_id=%s bytes=%s questions=%s", request_id, len(chunks), len(questions))
        if item["log_payloads"]:
            LOG.info("request request_id=%s payload=%s", request_id, chunks.decode())
        future = asyncio.get_running_loop().run_in_executor(pool, engine.infer, body, request_id)
        future.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
        try:
            # Keep worker ownership of the lock after timeout/disconnect until torch actually finishes.
            return await asyncio.wait_for(asyncio.shield(future), timeout=item["inference_timeout"])
        except asyncio.TimeoutError:
            LOG.error("inference_timeout request_id=%s; computation continues until completion", request_id)
            # Consume any later exception after the HTTP request has ended.
            return error(504, "inference timed out; worker remains busy until computation finishes")
        except (ValueError, TypeError, KeyError) as exc:
            return error(422, str(exc))
        except Exception:
            return error(500, "inference failed; see server log using request id")

    return app


def main() -> Any:
    load_local_environment()
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--model", required=True)
    add_overrides(ap)
    args = ap.parse_args()
    item = apply_overrides(config(args.config)[args.model], args)
    preflight(item)
    prepare_runtime(item)
    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    configure_logging(logs / (args.model + ".log"), item)
    sys.stdout, sys.stderr = LogStream(logging.INFO), LogStream(logging.WARNING)
    logging.captureWarnings(True)
    LOG.info("effective_config %s", json.dumps(item, ensure_ascii=False))
    engine = Engine(item)
    # Real warm-up before readiness, with all three Jev answer types.
    demo = {
        "state": "I was charged twice. Please refund me.",
        "questions": {
            "team": {
                "type": "choice",
                "instructions": "Which team?",
                "criteria": {"billing": "Payments", "tech": "Technical issues"},
            },
            "refund": {"type": "noul", "instructions": "Is a refund requested?"},
            "urgency": {"type": "score", "instructions": "How urgent?", "criteria": ["low", "high"]},
        },
    }
    if item["preload"]:
        engine.lock.acquire()
        engine.infer(demo, "startup-warmup")
    snapshot(ROOT / "run" / (args.model + ".effective.json"), item)
    import uvicorn

    uvicorn.run(
        create_app(item, engine),
        host=item["host"],
        port=item["port"],
        workers=1,
        log_level=item["log_level"].lower(),
        log_config=None,
        access_log=False,
        limit_concurrency=16,
        timeout_keep_alive=item["socket_timeout"],
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        LOG.exception("worker_fatal")
        raise
