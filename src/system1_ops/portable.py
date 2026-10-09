"""Windows/Linux process ownership, file locks, bounded logs and hardware snapshots."""

import json
import os
import pathlib
import platform
import subprocess
import time
from contextlib import contextmanager
from typing import Any


def probe_port(host: str, port: int) -> None:
    """Reject live listeners while permitting POSIX restarts with TIME_WAIT sockets."""
    import socket

    with socket.socket() as probe:
        if os.name == "nt":
            probe.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE"), 1)
        else:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind((host, port))


def identity(pid: int) -> float | None:
    import psutil

    try:
        process = psutil.Process(pid)
        if process.status() == psutil.STATUS_ZOMBIE:
            return None
        return process.create_time()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


@contextmanager
def file_lock(path: Any) -> Any:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt

            if path.stat().st_size == 0:
                handle.write(b"0")
                handle.flush()
            while True:
                try:
                    handle.seek(0)
                    getattr(msvcrt, "locking")(handle.fileno(), getattr(msvcrt, "LK_NBLCK"), 1)
                    break
                except OSError:
                    time.sleep(0.1)
            try:
                yield
            finally:
                handle.seek(0)
                getattr(msvcrt, "locking")(handle.fileno(), getattr(msvcrt, "LK_UNLCK"), 1)
        else:
            import fcntl

            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


def tail(path: Any, lines: Any = 100, max_bytes: Any = 65536) -> Any:
    try:
        with pathlib.Path(path).open("rb") as stream:
            stream.seek(0, 2)
            end = stream.tell()
            stream.seek(max(0, end - max_bytes))
            value = stream.read(max_bytes).decode("utf-8", errors="replace")
        return "\n".join(value.splitlines()[-lines:])
    except FileNotFoundError:
        return ""


def cpu_flags() -> list[str]:
    # On other platforms there is no reliable stdlib CPUID interface; conservative default.
    try:
        for line in pathlib.Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("flags"):
                return line.partition(":")[2].split()
    except OSError:
        pass
    return []


def hardware() -> dict[str, Any]:
    import psutil

    memory = psutil.virtual_memory()
    process = psutil.Process()
    result: dict[str, Any] = {
        "platform": platform.system(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "cpu": platform.processor(),
        "logical_cores": psutil.cpu_count(),
        "physical_cores": psutil.cpu_count(logical=False),
        "ram_total_mb": round(memory.total / 1024**2),
        "ram_available_mb": round(memory.available / 1024**2),
        "cpu_percent": psutil.cpu_percent(interval=None),
        "process_rss_mb": round(process.memory_info().rss / 1024**2, 1),
        "native_bf16": "avx512_bf16" in cpu_flags() or "amx_bf16" in cpu_flags(),
        "gpus": [],
    }
    if not result["cpu"] or result["cpu"] == platform.machine():
        try:
            result["cpu"] = next(
                line.partition(":")[2].strip()
                for line in pathlib.Path("/proc/cpuinfo").read_text().splitlines()
                if line.startswith("model name")
            )
        except (OSError, StopIteration):
            result["cpu"] = platform.machine()
    try:
        result["allowed_cpus"] = process.cpu_affinity()
    except (AttributeError, psutil.Error):
        result["allowed_cpus"] = None
    try:
        command = [
            "nvidia-smi",
            "--query-gpu=index,name,memory.total,memory.free,memory.used,utilization.gpu,driver_version",
            "--format=csv,noheader,nounits",
        ]
        reply = subprocess.run(command, capture_output=True, text=True, timeout=3)
        if reply.returncode:
            result["gpu_probe_error"] = (reply.stderr or reply.stdout).strip()[:500]
        else:
            for line in reply.stdout.splitlines():
                index, name, total, free, used, utilization, driver = [v.strip() for v in line.split(",")]
                result["gpus"].append(
                    {
                        "index": int(index),
                        "name": name,
                        "total_mb": int(total),
                        "free_mb": int(free),
                        "used_mb": int(used),
                        "utilization": utilization,
                        "driver": driver,
                    }
                )
    except (OSError, subprocess.TimeoutExpired, ValueError) as error:
        result["gpu_probe_error"] = str(error)[:500]
    return result


def gpu_process_memory(pids: Any) -> Any:
    """Observed resident GPU memory, not a peak or a PyTorch allocator metric."""
    try:
        reply = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,used_gpu_memory", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if reply.returncode:
            return None
        total = 0
        for line in reply.stdout.splitlines():
            pid, memory = (value.strip() for value in line.split(","))
            if int(pid) in pids:
                total += int(memory)
        return total
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def snapshot(path: Any, value: Any) -> Any:
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
