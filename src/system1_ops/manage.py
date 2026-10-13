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

from .common import (
    DEFAULT_CONFIG,
    ROOT,
    STATE,
    add_overrides,
    apply_overrides,
    config,
    load_local_environment,
    preflight,
)
from .portable import file_lock, identity, listener_pids, port_listened, probe_port, tail

RUN = STATE / "run"
LOGS = STATE / "logs"
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
    if port_listened(item["host"], item["port"]) and untracked_instance(item):
        # 本模型实例已在服务，只是没有管理记录：不重复启动，也不抛端口占用的原始异常。
        print(f"{name}: already running (no record) port={item['port']}; 用 stop 可接管该实例", flush=True)
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


def untracked_instance(item: Any) -> Any:
    """Health payload when the port's occupant identifies as this exact model, else None.

    Strict `model` equality keeps takeover limited to our own instances: a foreign
    JSON service that answers /health without a model field must never match.
    """
    try:
        payload = request(item)
    except (OSError, ValueError, urllib.error.URLError):
        return None
    return payload if payload.get("model") == item["name"] else None


def terminate_process(pid: Any, starttime: Any = None) -> Any:
    """Terminate one process and nothing else; escalate to kill while its identity persists.

    Graceful SIGTERM lets a worker run its own shutdown (engine unload, native helper
    stop) and lets a manager exit without touching the services it launched.
    """
    import psutil

    try:
        process = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
    moment = identity(pid) if starttime is None else starttime
    process.terminate()
    deadline = time.monotonic() + 30
    while moment is not None and identity(pid) == moment and time.monotonic() < deadline:
        time.sleep(0.2)
    if moment is not None and identity(pid) == moment:
        process.kill()


def terminate_tree(pid: Any, starttime: Any = None) -> Any:
    """Terminate a worker and its runtime children, e.g. the native GGUF helper.

    Only a model worker owns such children. A manager keeps the services it launched
    as children, so stopping or taking over one must never use this.
    """
    import psutil

    try:
        children = psutil.Process(pid).children(recursive=True)
    except psutil.NoSuchProcess:
        children = []
    terminate_process(pid, starttime)
    for child in children:
        try:
            child.terminate()
            child.wait(timeout=5)
        except psutil.TimeoutExpired:
            child.kill()
        except psutil.NoSuchProcess:
            pass


def stop(name: Any, item: Any = None) -> Any:
    value = record(name)
    managed_by_dashboard = item is not None and item.get("kind") == "dashboard"
    if value:
        # 运维台的子进程是它启动的模型服务，不是它自己的运行部件：只结束运维台本身。
        if managed_by_dashboard:
            terminate_process(value["pid"], value["starttime"])
        else:
            terminate_tree(value["pid"], value["starttime"])
        print(f"{name}: stopped PID={value['pid']}")
    elif item is not None and port_listened(item["host"], item["port"]) and untracked_instance(item):
        # 端口被本模型自己的实例占用，但没有可用的管理记录（例如进程在本记录之外启动）：
        # 按端口反查 PID 并接管，避免 stop/重启 静默失效。
        pids = listener_pids(item["port"])
        if not pids:
            raise RuntimeError(
                f"{name}: 端口 {item['port']} 上确认是本模型实例，但本进程无法解析它的 PID；"
                f"请在该实例的宿主上手动结束它（如 ss -ltnp | grep {item['port']}）后重试"
            )
        # 只结束占用端口的那个进程本身：它的子进程可能正是其它服务（如运维台启的模型），
        # 优雅 SIGTERM 会让它自己收尾原生助手等部件。
        for pid in pids:
            terminate_process(pid)
        print(f"{name}: stopped untracked PID={','.join(str(pid) for pid in pids)} port={item['port']}")
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
        RUN.mkdir(parents=True, exist_ok=True)
        LOGS.mkdir(parents=True, exist_ok=True)
        with file_lock(RUN / "manage.lock"):
            if args.model in ("all", "start"):
                start(item, args.config.resolve(), not args.no_wait)
            elif args.model == "stop":
                stop("dashboard", item)
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
    RUN.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
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
                    stop(name, item)
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
