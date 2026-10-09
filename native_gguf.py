"""C++ llama.cpp backend using upstream Jev rendering and calibrated readout."""
import json
import os
import subprocess
import time
import queue
import threading

from common import ROOT
from portable import identity, snapshot, probe_port


def load(item):
    if item.get("startlux_backend") == "gguf-stdio":
        return load_stdio(item)
    from startlux_decision.gguf_server import GGUFDecision
    from manage import HTTP
    probe_port("127.0.0.1", item["llama_port"])
    # One native inference slot, mmap enabled by llama.cpp's default. Only loopback
    # is exposed for the raw completion protocol; public clients use FastAPI.
    command = [item["llama_server"], "-m", item["gguf_file"], "--host", "127.0.0.1", "--port", str(item["llama_port"]),
               "-c", str(item["context_length"]), "-t", str(item["threads"]), "-tb", str(item["threads"]),
               "--parallel", "1", "-ngl", str(item["llama_gpu_layers"]),
               "--cache-type-k", item["llama_cache_type"], "--cache-type-v", item["llama_cache_type"]]
    path = ROOT / "logs" / (item["name"] + ".native.log")
    path.parent.mkdir(exist_ok=True)
    if path.exists():
        path.replace(path.with_suffix(".previous.log"))
    with path.open("ab", buffering=0) as output:
        process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                                   **({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}))
    snapshot(ROOT / "run" / (item["name"] + ".native.json"), {"pid": process.pid, "starttime": identity(process.pid)})
    deadline = time.monotonic() + item["startup_timeout"]
    base = f"http://127.0.0.1:{item['llama_port']}"
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"llama-server exited {process.returncode}; see {path}")
            try:
                with HTTP.open(base + "/health", timeout=2) as response:
                    if json.load(response).get("status") == "ok":
                        model = GGUFDecision(item["path"], base, workers=1)
                        model.max_length = item["context_length"]
                        return model, process
            except OSError:
                pass
            time.sleep(0.5)
        raise RuntimeError("llama-server readiness timeout")
    except Exception:
        process.terminate()
        process.wait(timeout=10)
        raise


def load_stdio(item):
    from startlux_decision.gguf_server import GGUFDecision
    path = ROOT / "logs" / (item["name"] + ".native.log")
    path.parent.mkdir(exist_ok=True)
    if path.exists() and path.stat().st_size >= item["log_max_bytes"]:
        for number in range(item["log_backups"] - 1, 0, -1):
            older = path.with_name(path.name + f".{number}")
            if older.exists():
                older.replace(path.with_name(path.name + f".{number + 1}"))
        path.replace(path.with_name(path.name + ".1"))
    command = [item["native_binary"], item["gguf_file"], str(item["context_length"]),
               str(item["threads"]), str(item["llama_gpu_layers"])]
    with path.open("ab", buffering=0) as output:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=output,
                                   text=True, encoding="utf-8", bufsize=1,
                                   **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}))
    snapshot(ROOT / "run" / (item["name"] + ".native.json"), {"pid": process.pid, "starttime": identity(process.pid)})
    replies = queue.Queue(maxsize=2)

    def read():
        try:
            for line in process.stdout:
                replies.put(json.loads(line))
        except Exception as error:
            replies.put({"error": str(error)})
        finally:
            replies.put({"error": "native engine exited"})

    threading.Thread(target=read, daemon=True, name="native-output").start()

    def receive(timeout):
        try:
            result = replies.get(timeout=timeout)
        except queue.Empty:
            stop_process(process)
            raise RuntimeError(f"native response timeout; see {path}") from None
        if "error" in result:
            raise RuntimeError(result["error"])
        return result

    try:
        ready = receive(item["startup_timeout"])
        if ready.get("ready") is not True:
            raise RuntimeError("native engine did not return readiness")

        class PipeDecision(GGUFDecision):
            def _letter_logprobs(self, ids, count):
                process.stdin.write(json.dumps({"tokens": ids, "letters": self.letters[:count]}) + "\n")
                process.stdin.flush()
                values = receive(item["inference_timeout"])["logits"]
                if len(values) != count:
                    raise RuntimeError("native readout length mismatch")
                return values

        model = PipeDecision(item["path"], "http://unused", workers=1)
        model.max_length = item["context_length"]
        return model, process
    except Exception:
        stop_process(process)
        raise


def stop_process(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
