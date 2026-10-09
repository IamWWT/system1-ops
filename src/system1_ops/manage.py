#!/usr/bin/env python3
"""Local process manager. All writable state stays beside these scripts."""

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from .common import DEFAULT_CONFIG, ROOT, add_overrides, apply_overrides, config, load_local_environment, preflight
from .portable import file_lock, identity, probe_port, tail

RUN = ROOT / "run"
LOGS = ROOT / "logs"
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
SMOKE: dict[str, Any] = {
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


def record(name: Any) -> Any:
    path = RUN / (name + ".json")
    try:
        value = json.loads(path.read_text())
        if value["starttime"] is not None and identity(value["pid"]) == value["starttime"]:
            return value
    except (OSError, ValueError, KeyError):
        pass
    return None


def request(item: Any, route: Any = "/health", body: Any = None) -> Any:
    host = "127.0.0.1" if item["host"] == "0.0.0.0" else item["host"]
    headers = {"Content-Type": "application/json"}
    key = os.environ.get(item["api_key_env"], "")
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(
        f"http://{host}:{item['port']}{route}", data=json.dumps(body).encode() if body else None, headers=headers
    )
    with HTTP.open(req, timeout=item["inference_timeout"] if body else 2) as response:
        result = json.load(response)
    if result.get("model") not in (None, item["name"]):
        raise ValueError("port occupied by another model")
    return result


def start(item: Any, config_path: Any, wait: Any = True) -> Any:
    name = item["name"]
    if record(name):
        print(f"{name}: already running PID={record(name)['pid']}")
        return
    native = preflight(item) if item["kind"] != "dashboard" else None
    # Fail before loading GBs of weights, but allow a stopped server's TIME_WAIT.
    probe_port(item["host"], item["port"])
    boot = LOGS / (name + ".console.log")
    if boot.exists():
        boot.replace(LOGS / (name + ".console.previous.log"))
    with boot.open("ab", buffering=0) as output:
        process = subprocess.Popen(
            [
                item["python"],
                "-u",
                str(ROOT / "scripts" / "launch.py"),
                "dashboard" if item["kind"] == "dashboard" else "worker",
                "--config",
                str(config_path),
                "--model",
                name,
                "--port",
                str(item["port"]),
                "--device",
                item["device"],
                "--context-length",
                str(item["context_length"]),
            ],
            cwd=ROOT,
            stdout=output,
            stderr=subprocess.STDOUT,
            **(
                {
                    "creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP")
                    | getattr(subprocess, "DETACHED_PROCESS")
                }
                if os.name == "nt"
                else {"start_new_session": True}
            ),
        )
    value = {
        "pid": process.pid,
        "starttime": identity(process.pid),
        "port": item["port"],
        "host": item["host"],
        "name": name,
        "config": str(config_path),
    }
    (RUN / (name + ".json")).write_text(json.dumps(value))
    print(f"{name}: launched PID={process.pid} port={item['port']} native_context={native} log={boot}", flush=True)
    if not wait:
        return
    deadline = time.monotonic() + item["startup_timeout"]
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{name}: startup exited {process.returncode}; see {boot}")
        try:
            health = request(item)
            if health.get("status") == "ok":
                print(f"{name}: ready {json.dumps(health, ensure_ascii=False)}", flush=True)
                return
        except (OSError, ValueError, urllib.error.URLError):
            pass
        time.sleep(1)
    raise RuntimeError(f"{name}: readiness timed out; process remains running, inspect logs/status or stop it")


def stop(name: Any) -> Any:
    value = record(name)
    if value:
        import psutil

        process = psutil.Process(value["pid"])
        children = process.children(recursive=True)
        process.terminate()
        deadline = time.monotonic() + 30
        while identity(value["pid"]) == value["starttime"] and time.monotonic() < deadline:
            time.sleep(0.2)
        if identity(value["pid"]) == value["starttime"]:
            process.kill()
        for child in children:
            try:
                child.terminate()
                child.wait(timeout=5)
            except psutil.TimeoutExpired:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        print(f"{name}: stopped PID={value['pid']}")
    else:
        print(f"{name}: not running")
    (RUN / (name + ".json")).unlink(missing_ok=True)


def doctor(item: Any) -> Any:
    native = preflight(item)
    # Match worker import order: fallback packages follow this interpreter's own
    # site-packages, otherwise a shared CPU torch can mask a CUDA installation.
    code = (
        "import json,sys; from system1_ops.common import prepare_runtime; prepare_runtime(json.loads(sys.stdin.read())); "
        "import torch,transformers,fastapi,uvicorn; print('torch='+torch.__version__, "
        "'transformers='+transformers.__version__, 'torch_cuda='+str(torch.cuda.is_available()))"
    )
    result = subprocess.run(
        [item["python"], "-c", code],
        input=json.dumps(item),
        cwd=ROOT,
        env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    print(f"{item['name']}: checkpoint complete, native_context={native}; {result.stdout.strip()}")


def main() -> Any:
    load_local_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["start", "stop", "restart", "status", "health", "smoke", "doctor", "logs", "config", "dashboard"],
    )
    parser.add_argument("model", nargs="?", default="all")
    parser.add_argument("--config", type=pathlib.Path, default=DEFAULT_CONFIG)
    parser.add_argument("--no-wait", action="store_true")
    parser.add_argument("--follow", action="store_true")
    add_overrides(parser)
    args = parser.parse_args()
    if args.command == "dashboard":
        import tomllib

        with args.config.open("rb") as source:
            ui = tomllib.load(source).get("dashboard", {})
        item = {
            "name": "dashboard",
            "kind": "dashboard",
            "python": sys.executable,
            "host": ui.get("host", "0.0.0.0"),
            "port": args.port or ui.get("port", 8885),
            "device": "cpu",
            "context_length": 8192,
            "startup_timeout": 30,
            "inference_timeout": 60,
            "api_key_env": "SYSTEM1_ADMIN_KEY",
        }
        RUN.mkdir(exist_ok=True)
        LOGS.mkdir(exist_ok=True)
        with file_lock(RUN / "manage.lock"):
            if args.model in ("all", "start"):
                start(item, args.config.resolve(), not args.no_wait)
            elif args.model == "stop":
                stop("dashboard")
            elif args.model == "status":
                print(json.dumps({"process": record("dashboard")}))
            else:
                parser.error("dashboard start|stop|status")
        return 0
    items = config(args.config)
    if args.model != "all" and args.model not in items:
        parser.error("unknown model: " + args.model)
    selected = list(items.values()) if args.model == "all" else [items[args.model]]
    if args.port and len(selected) != 1:
        parser.error("--port requires one named model")
    selected = [apply_overrides(item, args) for item in selected]
    RUN.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    failed = False
    # Serialize lifecycle changes, even when invoked from different terminals.
    with (
        file_lock(RUN / "manage.lock")
        if args.command in ("start", "stop", "restart")
        else __import__("contextlib").nullcontext()
    ):
        for item in selected:
            name = item["name"]
            try:
                if args.command == "config":
                    print(json.dumps(item, indent=2, ensure_ascii=False))
                elif args.command == "doctor":
                    doctor(item)
                elif args.command == "logs":
                    paths = [str(p) for p in (LOGS / (name + ".console.log"), LOGS / (name + ".log")) if p.exists()]
                    if not paths:
                        print(f"{name}: no log yet")
                    else:
                        for path in paths:
                            print(f"== {path} ==\n{tail(path, 80)}")
                        if args.follow:
                            previous = {path: tail(path, 80) for path in paths}
                            while True:
                                time.sleep(1)
                                for path in paths:
                                    value = tail(path, 80)
                                    if value != previous[path]:
                                        print(f"== {path} ==\n{value}", flush=True)
                                        previous[path] = value
                elif args.command in ("stop", "restart"):
                    stop(name)
                    if args.command == "restart":
                        start(item, args.config.resolve(), not args.no_wait)
                elif args.command == "start":
                    start(item, args.config.resolve(), not args.no_wait)
                elif args.command == "status":
                    pid = record(name)
                    print(f"{name}: " + (f"running PID={pid['pid']} port={pid['port']}" if pid else "stopped"))
                    if pid:
                        print(json.dumps(request(dict(item, port=pid["port"], host=pid["host"])), ensure_ascii=False))
                else:
                    result = request(item, "/v1/systemone", SMOKE) if args.command == "smoke" else request(item)
                    if args.command == "smoke":
                        if set(result["answers"]) != set(SMOKE["questions"]):
                            raise ValueError("smoke failed: missing answers")
                        for qid, q in SMOKE["questions"].items():
                            if result["answers"][qid]["type"] != q["type"]:
                                raise ValueError("smoke failed: answer type mismatch")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
            except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
                failed = True
                print(f"{name}: ERROR {exc}", file=sys.stderr, flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
