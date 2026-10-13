"""Local operations UI on 8885. Model ports keep the Jev protocol unchanged."""

import argparse
import asyncio
import json
import logging
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from functools import partial
from typing import Any

from .common import DEFAULT_CONFIG, ROOT, STATE, add_overrides, bearer_matches, config, load_local_environment
from .logging_config import configure_logging
from .manage import LOGS, RUN, record, request, start, stop
from .portable import file_lock, hardware, port_listened, tail


def create_dashboard(config_path: Any = DEFAULT_CONFIG) -> Any:
    from fastapi import FastAPI, Request
    from fastapi.responses import FileResponse, JSONResponse

    items = config(config_path)
    key = os.environ.get("SYSTEM1_ADMIN_KEY", "")
    jobs: dict[str, Any] = {}
    running: set[str] = set()
    tasks: set[asyncio.Task[Any]] = set()
    pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="operations")

    async def blocking(function: Any, *args: Any) -> Any:
        return await asyncio.get_running_loop().run_in_executor(pool, partial(function, *args))

    @asynccontextmanager
    async def lifespan(app: Any) -> Any:
        yield
        # Operations threads own process lifecycles; finish before dashboard exits.
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        pool.shutdown(wait=True)

    app = FastAPI(title="System 1 Operations", lifespan=lifespan)

    @app.middleware("http")
    async def authorization(req: Any, call_next: Any) -> Any:
        if req.url.path.startswith("/ops/"):
            authenticated = bearer_matches(req.headers.get("authorization", ""), key)
            if key and not authenticated:
                return JSONResponse({"error": "admin key required"}, status_code=401)
            if req.method != "GET" and not authenticated:
                return JSONResponse(
                    {"error": "set SYSTEM1_ADMIN_KEY and enter it on the page to enable controls"}, status_code=403
                )
        return await call_next(req)

    @app.middleware("http")
    async def audit(req: Request, call_next: Any) -> Any:
        request_id = uuid.uuid4().hex
        began = time.monotonic()
        response = await call_next(req)
        response.headers["x-request-id"] = request_id
        logging.getLogger("system1.ops").info(
            "ops_http",
            extra={
                "request_id": request_id,
                "client": req.client.host if req.client else "",
                "actor": "admin" if bearer_matches(req.headers.get("authorization", ""), key) else "anonymous",
                "method": req.method,
                "path": req.url.path,
                "http_status": response.status_code,
                "latency_ms": round(1000 * (time.monotonic() - began), 3),
            },
        )
        return response

    @app.get("/")
    def index() -> Any:
        return FileResponse(pathlib.Path(__file__).parent / "web" / "index.html", headers={"Cache-Control": "no-store"})

    @app.get("/app.js")
    def javascript() -> Any:
        return FileResponse(
            pathlib.Path(__file__).parent / "web" / "app.js",
            media_type="application/javascript",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/health")
    def health() -> Any:
        return {"status": "ok", "model": "dashboard"}

    def status(name: Any, item: Any) -> Any:
        owned = record(name)
        output = {
            "name": name,
            "port": item["port"],
            "running": owned is not None,
            "unmanaged": False,
            "health": None,
            "error": None,
            "config": item,
        }
        effective = RUN / (name + ".effective.json")
        if owned and effective.exists():
            output["config"] = json.loads(effective.read_text(encoding="utf-8"))
        if owned:
            output["pid"] = owned["pid"]
            output["port"] = owned["port"]
            try:
                output["health"] = request(dict(item, port=owned["port"], host=owned["host"]))
            except (OSError, ValueError) as error:
                output["error"] = str(error)
        else:
            from .common import preflight

            if port_listened(item["host"], item["port"]):
                # 无管理记录但端口在用：占用者可能是本模型的实例（进程不由本记录跟踪），
                # 这时按“运行中（未纳入管理记录）”呈现，而不是报“已停止 + 端口被占用”。
                try:
                    output["health"] = request(item)
                except (OSError, ValueError, urllib.error.URLError):
                    output["error"] = f"端口 {item['port']} 被占用，可能有残留进程或其他服务"
                else:
                    output["running"] = True
                    output["unmanaged"] = True
                return output
            try:
                preflight(item)
            except (OSError, ValueError) as error:
                output["error"] = str(error)
        return output

    @app.get("/ops/state")
    async def state() -> Any:
        models, host = await asyncio.gather(
            asyncio.gather(*(blocking(status, name, item) for name, item in items.items())), blocking(hardware)
        )
        return {"models": models, "hardware": host, "controls_enabled": bool(key), "time": time.time()}

    @app.get("/ops/models/{name}/check")
    async def check_model(name: str) -> Any:
        """On-demand status check: process, /health, load state, port and preflight."""
        if name not in items:
            return JSONResponse({"error": "unknown model"}, status_code=404)
        item = items[name]
        owned = record(name)
        result: dict[str, Any] = {
            "name": name,
            "checked_at": time.time(),
            "managed": owned is not None,
            "unmanaged": False,
            "pid": owned["pid"] if owned else None,
            "port": owned["port"] if owned else item["port"],
            "reachable": False,
            "health": None,
            "port_in_use": False,
            "preflight": None,
            "error": None,
        }
        if owned:
            probe = dict(item, port=owned["port"], host=owned["host"])
            try:
                result["health"] = await blocking(request, probe)
                result["reachable"] = bool(result["health"].get("status") == "ok")
            except (OSError, ValueError, urllib.error.URLError) as error:
                result["error"] = str(error)
        else:
            result["port_in_use"] = await blocking(port_listened, item["host"], item["port"])
            if result["port_in_use"]:
                # 端口在用不等于异常：占用者可能正是本模型的实例，只是没有管理记录跟踪它。
                # request() 校验 /health 的 model 字段，占用者不是本模型时抛 ValueError。
                try:
                    result["health"] = await blocking(request, item)
                    result["reachable"] = bool(result["health"].get("status") == "ok")
                    result["unmanaged"] = True
                except (OSError, ValueError, urllib.error.URLError):
                    result["error"] = f"端口 {item['port']} 被占用，可能有残留进程或其他服务"
            else:
                from .common import preflight

                try:
                    result["preflight"] = await blocking(preflight, item)
                except (OSError, ValueError) as error:
                    result["error"] = str(error)
        return result

    @app.get("/ops/models/{name}/logs")
    def logs(name: str) -> Any:
        if name not in items:
            return JSONResponse({"error": "unknown model"}, status_code=404)
        return {
            "text": tail(LOGS / (name + ".log"), 200)
            + "\n"
            + tail(LOGS / (name + ".console.log"), 40)
            + "\n"
            + tail(LOGS / (name + ".native.log"), 80)
        }

    @app.get("/ops/reports")
    def reports() -> Any:
        report = STATE / "reports" / "latest.json"
        return (
            json.loads(report.read_text(encoding="utf-8"))
            if report.exists()
            else {"results": [], "recommendations": {}}
        )

    async def job(operation: Any, name: Any, action: Any) -> Any:
        token = uuid.uuid4().hex
        jobs[token] = {"id": token, "model": name, "action": action, "status": "running", "started_at": time.time()}
        running.add(name)

        async def execute():
            try:
                await blocking(operation)
                jobs[token]["status"] = "done"
            except Exception as error:
                jobs[token].update(status="failed", error=str(error))
            finally:
                running.discard(name)
                jobs[token]["finished_at"] = time.time()
                # Keep a bounded in-memory operation history.
                for old in list(jobs)[:-100]:
                    if jobs[old]["status"] != "running":
                        jobs.pop(old)

        task = asyncio.create_task(execute())
        tasks.add(task)
        task.add_done_callback(tasks.discard)
        return JSONResponse(jobs[token], status_code=202)

    @app.get("/ops/jobs/{token}")
    def get_job(token: str) -> Any:
        return jobs.get(token) or JSONResponse({"error": "unknown job"}, status_code=404)

    @app.post("/ops/models/{name}/{action}")
    async def control(name: str, action: str) -> Any:
        if name not in items or action not in ("start", "stop", "restart", "benchmark"):
            return JSONResponse({"error": "unknown model/action"}, status_code=404)
        if name in running or "benchmark" in running:
            return JSONResponse({"error": "operation already running"}, status_code=409)

        def operation():
            if action == "benchmark":
                with file_lock(RUN / "benchmark.lock"):
                    with (LOGS / "benchmark.log").open("a", encoding="utf-8") as output:
                        subprocess.run(
                            [
                                sys.executable,
                                str(ROOT / "scripts" / "benchmark.py"),
                                "--model",
                                name,
                                "--config",
                                str(config_path),
                                "--preset",
                                "quick",
                            ],
                            stdout=output,
                            stderr=output,
                            check=True,
                        )
            else:
                with file_lock(RUN / "manage.lock"):
                    if action in ("stop", "restart"):
                        stop(name, items[name])
                    if action in ("start", "restart"):
                        start(items[name], pathlib.Path(config_path).resolve())

        return await job(operation, "benchmark" if action == "benchmark" else name, action)

    @app.post("/ops/debug/{name}")
    async def debug(name: str, req: Request) -> Any:
        if name not in items:
            return JSONResponse({"error": "unknown model"}, status_code=404)
        raw = bytearray()
        async for chunk in req.stream():
            if len(raw) + len(chunk) > 1024 * 1024:
                return JSONResponse({"error": "debug body exceeds 1MB"}, status_code=413)
            raw.extend(chunk)
        try:
            body = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            return JSONResponse({"error": "invalid JSON"}, status_code=400)
        item = items[name]
        owned = record(name)
        if owned:
            item = dict(item, port=owned["port"], host=owned["host"])
        began = time.monotonic()
        try:
            response = await blocking(request, item, "/v1/systemone", body)
            return {"http_status": 200, "latency_ms": 1000 * (time.monotonic() - began), "body": response}
        except urllib.error.HTTPError as error:
            return {
                "http_status": error.code,
                "body": json.loads(error.read()),
                "latency_ms": 1000 * (time.monotonic() - began),
            }
        except (OSError, ValueError) as error:
            return JSONResponse({"error": str(error)}, status_code=502)

    return app


def main() -> Any:
    load_local_environment()
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=pathlib.Path, default=DEFAULT_CONFIG)
    parser.add_argument("--model", default="dashboard")
    parser.add_argument("--host")
    add_overrides(parser)
    args = parser.parse_args()
    import tomllib

    with args.config.open("rb") as source:
        settings = tomllib.load(source).get("dashboard", {})
    RUN.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    import uvicorn

    configure_logging(LOGS / "dashboard.log", next(iter(config(args.config).values())))
    uvicorn.run(
        create_dashboard(args.config),
        host=args.host or settings.get("host", "0.0.0.0"),
        port=args.port or settings.get("port", 8885),
        proxy_headers=False,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
