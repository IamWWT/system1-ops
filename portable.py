"""Windows/Linux process ownership, file locks, bounded logs and hardware snapshots."""
from contextlib import contextmanager
import json
import os
import pathlib
import platform
import subprocess
import time


def identity(pid):
    import psutil
    try:
        process = psutil.Process(pid)
        if process.status() == psutil.STATUS_ZOMBIE:
            return None
        return process.create_time()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


@contextmanager
def file_lock(path):
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
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


def tail(path, lines=100, max_bytes=65536):
    try:
        with pathlib.Path(path).open("rb") as stream:
            stream.seek(0, 2)
            end = stream.tell()
            stream.seek(max(0, end - max_bytes))
            value = stream.read(max_bytes).decode("utf-8", errors="replace")
        return "\n".join(value.splitlines()[-lines:])
    except FileNotFoundError:
        return ""


def cpu_flags():
    # On other platforms there is no reliable stdlib CPUID interface; conservative default.
    try:
        for line in pathlib.Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("flags"):
                return line.partition(":")[2].split()
    except OSError:
        pass
    return []


def hardware():
    import psutil
    memory = psutil.virtual_memory()
    process = psutil.Process()
    result = {"platform": platform.system(), "machine": platform.machine(),
              "python": platform.python_version(), "cpu": platform.processor(),
              "logical_cores": psutil.cpu_count(), "physical_cores": psutil.cpu_count(logical=False),
              "ram_total_mb": round(memory.total / 1024**2), "ram_available_mb": round(memory.available / 1024**2),
              "cpu_percent": psutil.cpu_percent(interval=None), "process_rss_mb": round(process.memory_info().rss / 1024**2, 1),
              "native_bf16": "avx512_bf16" in cpu_flags() or "amx_bf16" in cpu_flags(), "gpus": []}
    if not result["cpu"] or result["cpu"] == platform.machine():
        try:
            result["cpu"] = next(line.partition(":")[2].strip() for line in pathlib.Path("/proc/cpuinfo").read_text().splitlines()
                                 if line.startswith("model name"))
        except (OSError, StopIteration):
            result["cpu"] = platform.machine()
    try:
        result["allowed_cpus"] = process.cpu_affinity()
    except (AttributeError, psutil.Error):
        result["allowed_cpus"] = None
    try:
        command = ["nvidia-smi", "--query-gpu=index,name,memory.total,memory.free,memory.used,utilization.gpu,driver_version",
                   "--format=csv,noheader,nounits"]
        reply = subprocess.run(command, capture_output=True, text=True, timeout=3)
        if reply.returncode:
            result["gpu_probe_error"] = (reply.stderr or reply.stdout).strip()[:500]
        else:
            for line in reply.stdout.splitlines():
                index, name, total, free, used, utilization, driver = [v.strip() for v in line.split(",")]
                result["gpus"].append({"index": int(index), "name": name, "total_mb": int(total),
                                       "free_mb": int(free), "used_mb": int(used), "utilization": utilization,
                                       "driver": driver})
    except (OSError, subprocess.TimeoutExpired, ValueError) as error:
        result["gpu_probe_error"] = str(error)[:500]
    return result


def snapshot(path, value):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
