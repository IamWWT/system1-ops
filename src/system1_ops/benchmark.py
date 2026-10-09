"""Isolated, correctness-gated latency/memory sweeps; Linux and Windows CPU/CUDA.

Each candidate runs in a new process. Raw outputs and failures are retained. No
recommendation is applied automatically or transplanted to a different machine.
"""

import argparse
import hashlib
import json
import logging
import pathlib
import statistics
import subprocess
import threading
import time
from typing import Any

from .common import DEFAULT_CONFIG, ROOT, STATE, config, preflight, prepare_runtime
from .portable import gpu_process_memory, hardware, snapshot


def fixtures(preset: Any) -> Any:
    questions = {
        "team": {
            "type": "choice",
            "instructions": "Which team should handle this request?",
            "criteria": {
                "billing": "Payments, invoices, refunds",
                "technical": "Login and app problems",
                "other": "Other requests",
            },
        },
        "refund": {"type": "noul", "instructions": "Does the customer request a refund?"},
        "severity": {
            "type": "score",
            "instructions": "How severe is the issue?",
            "criteria": ["minor", "moderate", "severe"],
        },
    }
    seeds = [
        ("billing", "I was charged twice for my order. Please refund the duplicate charge."),
        ("technical", "I cannot log into my account. Password reset fails with an error."),
    ]
    sizes = [0, 32] if preset == "quick" else [0, 32, 128, 512]
    return [
        {
            "id": f"{name}-{size}",
            "body": {
                "state": "The customer has an active subscription and an account on the platform. " * size + text,
                "questions": questions,
            },
        }
        for size in sizes
        for name, text in seeds
    ]


def compatibility(reference: Any, candidate: Any) -> Any:
    drift, agreements, count = 0.0, 0, 0
    for case, expected in reference.items():
        if case not in candidate:
            return {"choice_agreement": 0, "max_probability_delta": 1, "passed": False, "reason": "missing case"}
        for name, answer in expected["answers"].items():
            actual = candidate[case]["answers"][name]
            if answer["type"] == "choice":
                count += 1
                agreements += answer["choice"] == actual["choice"]
            for key in ("noul", "score", "confidence"):
                if key in answer:
                    # Score also has probabilities; scale the expected-index delta to [0,1].
                    scale = max(1, len(answer.get("probabilities", {})) - 1) if key == "score" else 1
                    drift = max(drift, abs(answer[key] - actual[key]) / scale)
            for key, probability in answer.get("probabilities", {}).items():
                drift = max(drift, abs(probability - actual.get("probabilities", {}).get(key, -1)))
    return {
        "choice_agreement": agreements / max(1, count),
        "max_probability_delta": drift,
        "passed": agreements == count and drift <= 0.02,
        "meaning": "numerical compatibility on synthetic fixtures, not task accuracy",
    }


def run_worker(args: Any) -> Any:
    item = json.loads(args.item.read_text(encoding="utf-8"))
    prepare_runtime(item)
    import psutil
    import torch

    from .worker import Engine

    native = item.get("startlux_backend", "torch").startswith("gguf")
    report = {
        "candidate": args.item.stem,
        "model": item["name"],
        "settings": {
            k: item.get(k)
            for k in (
                "device",
                "threads",
                "cpu_dtype",
                "cpu_quantization",
                "laya_backend",
                "laya_gpu_dtype",
                "laya_gpu_tf32",
                "serialize_inference",
                "unload_after_request",
                "cuda_graphs",
                "window_length",
                "cpu_affinity",
                "startlux_backend",
            )
        },
        "status": "failed",
        "hardware": hardware(),
    }
    if item["device"].startswith("cuda") and not (hardware()["gpus"] if native else torch.cuda.is_available()):
        report.update(status="skipped", reason="CUDA unavailable in this runtime")
        snapshot(args.output, report)
        return
    engine = Engine(item)
    process = psutil.Process()
    peak = [process.memory_info().rss]
    finished = threading.Event()

    def sample() -> Any:
        while not finished.wait(0.02):
            rss = process.memory_info().rss
            for child in process.children(recursive=True):
                try:
                    rss += child.memory_info().rss
                except psutil.NoSuchProcess:
                    pass
            peak[0] = max(peak[0], rss)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    started = time.monotonic()
    cpu_started = process.cpu_times()
    try:
        engine.load()
        assert engine.device is not None
        report["load_ms"] = 1000 * (time.monotonic() - started)
        tests = fixtures(args.preset)
        # Cold inference and warm inference are separate; warm-up is not timed into p50.
        engine.lock.acquire()
        engine.infer(tests[0]["body"], "benchmark-warmup")
        times, outputs = [], {}
        for case in tests:
            for repeat in range(args.repeats):
                engine.lock.acquire()
                if engine.device.startswith("cuda") and not native:
                    torch.cuda.synchronize()
                before = time.perf_counter()
                result = engine.infer(case["body"], f"benchmark-{case['id']}-{repeat}")
                if engine.device.startswith("cuda") and not native:
                    torch.cuda.synchronize()
                times.append(
                    {
                        "case": case["id"],
                        "repeat": repeat,
                        "ms": 1000 * (time.perf_counter() - before),
                        "usage": result["usage"],
                    }
                )
                outputs[case["id"]] = result
        elapsed = [value["ms"] for value in times]
        cpu_finished = process.cpu_times()
        child_cpu_seconds = sum(c.cpu_times().user + c.cpu_times().system for c in process.children(recursive=True))
        gpu_resident = (
            gpu_process_memory({process.pid, *(c.pid for c in process.children(recursive=True))})
            if engine.device.startswith("cuda")
            else None
        )
        report.update(
            status="ok",
            actual_device=engine.device,
            precision=engine.precision,
            actual_backend=engine.backend,
            p50_ms=statistics.median(elapsed),
            p95_ms=sorted(elapsed)[max(0, int(len(elapsed) * 0.95 + 0.999) - 1)],
            timings=times,
            outputs=outputs,
            peak_rss_mb=peak[0] / 1024**2,
            cpu_seconds=(
                cpu_finished.user + cpu_finished.system - cpu_started.user - cpu_started.system + child_cpu_seconds
            ),
            nvidia_resident_mb=gpu_resident,
            cuda_peak_allocated_mb=torch.cuda.max_memory_allocated() / 1024**2
            if engine.device.startswith("cuda") and not native
            else None,
            cuda_peak_reserved_mb=torch.cuda.max_memory_reserved() / 1024**2
            if engine.device.startswith("cuda") and not native
            else None,
        )
    except Exception as error:
        logging.exception("benchmark candidate failed")
        report.update(reason=str(error), peak_rss_mb=peak[0] / 1024**2)
    finally:
        finished.set()
        sampler.join()
        if engine.model is not None:
            engine.unload()
        report["rss_after_unload_mb"] = process.memory_info().rss / 1024**2
        snapshot(args.output, report)


def release_port(port: Any) -> Any:
    """Only the explicitly requested listener; never infer ownership from command text."""
    import psutil

    listeners = {
        connection.pid
        for connection in psutil.net_connections(kind="tcp")
        if connection.status == psutil.CONN_LISTEN
        and connection.laddr
        and connection.laddr.port == port
        and connection.pid
    }
    if not listeners:
        raise RuntimeError(f"no identifiable listener on {port}; no process stopped")
    for pid in listeners:
        process = psutil.Process(pid)
        print(f"Stopping authorized port {port}: PID={pid} name={process.name()}", flush=True)
        process.terminate()
        try:
            process.wait(timeout=20)
        except psutil.TimeoutExpired:
            raise RuntimeError(f"PID {pid} did not stop; no force-kill performed") from None
    # Parent launchers may restart the service; check before claiming GPU was freed.
    time.sleep(1)
    if any(
        connection.status == psutil.CONN_LISTEN and connection.laddr and connection.laddr.port == port
        for connection in psutil.net_connections(kind="tcp")
    ):
        raise RuntimeError(f"{port} still listening or was restarted by its supervisor")


def sweep(args: Any) -> Any:
    if args.release_port is not None:
        if args.release_port != 8881:
            raise ValueError("this run is authorized to release port 8881 only")
        release_port(args.release_port)
    items = config(args.config)
    selected = list(items.values()) if args.model == "all" else [items[args.model]]
    results = []
    stamp = time.strftime("%Y%m%d-%H%M%S")
    directory = STATE / "reports" / stamp
    directory.mkdir(parents=True)
    repeats = args.repeats or (2 if args.preset == "quick" else 5)
    for item in selected:
        try:
            preflight(item)
        except (ValueError, OSError) as error:
            results.append({"model": item["name"], "status": "skipped", "reason": str(error)})
            continue
        baseline = dict(
            item,
            device="cpu",
            threads=4,
            cpu_dtype="bf16" if item["kind"] == "startlux" else "fp32",
            cpu_quantization="none",
            laya_backend="eager",
            cuda_graphs=False,
            cpu_affinity=[],
        )
        candidates = [("reference", baseline)]
        native_configured = item.get("startlux_backend", "torch").startswith("gguf")
        for threads in [1, 2, 4, 8] if args.preset == "quick" else [1, 2, 4, 8, 16]:
            tag = "cpp-gguf" if native_configured else "cpu-fp32"
            candidates.append((f"{tag}-t{threads}", dict(baseline, threads=threads, cpu_dtype="fp32")))
        if item["kind"] == "laya":
            candidates.append(("cpu-int8-t4", dict(baseline, cpu_quantization="int8")))
        elif not native_configured and item.get("gguf_file") and item.get("native_binary"):
            for threads in (2, 4, 8):
                candidates.append(
                    (f"cpp-gguf-t{threads}", dict(baseline, threads=threads, startlux_backend="gguf-stdio"))
                )
        if "cpu" not in args.devices:
            candidates = candidates[:1]  # Keep the reference needed for compatibility checks.
        if "cuda" in args.devices:
            if native_configured:
                candidates.append(("cuda-native", dict(baseline, device="cuda:0")))
            elif item["kind"] == "laya":
                for backend in ("eager", "compile", "tilelang"):
                    candidates.append(("cuda-" + backend, dict(baseline, device="cuda:0", laya_backend=backend)))
            else:
                for graphs in (False, True):
                    candidates.append(
                        ("cuda-graphs-" + str(graphs).lower(), dict(baseline, device="cuda:0", cuda_graphs=graphs))
                    )
        reference = None
        for tag, settings in candidates:
            name = item["name"] + "-" + tag
            input_path = STATE / "run" / (name + ".json")
            output_path = directory / (name + ".json")
            snapshot(input_path, settings)
            print(f"benchmark {name}", flush=True)
            with (directory / (name + ".log")).open("w", encoding="utf-8") as log:
                try:
                    process = subprocess.Popen(
                        [
                            item["python"],
                            "-u",
                            str(ROOT / "scripts" / "launch.py"),
                            "benchmark",
                            "--item",
                            str(input_path),
                            "--output",
                            str(output_path),
                            "--preset",
                            args.preset,
                            "--repeats",
                            str(repeats),
                        ],
                        stdout=log,
                        stderr=log,
                    )
                    try:
                        process.wait(timeout=args.candidate_timeout)
                    except subprocess.TimeoutExpired:
                        import psutil

                        try:
                            for child in psutil.Process(process.pid).children(recursive=True):
                                try:
                                    child.kill()
                                except psutil.NoSuchProcess:
                                    pass
                        except psutil.NoSuchProcess:
                            pass
                        process.kill()
                        process.wait(timeout=10)
                        raise
                    result = (
                        json.loads(output_path.read_text(encoding="utf-8"))
                        if output_path.exists()
                        else {
                            "model": item["name"],
                            "candidate": name,
                            "status": "failed",
                            "reason": f"worker exited {process.returncode}; see log",
                        }
                    )
                except subprocess.TimeoutExpired:
                    result = {
                        "model": item["name"],
                        "candidate": name,
                        "status": "failed",
                        "reason": "candidate timeout",
                    }
            input_path.unlink(missing_ok=True)
            if result["status"] == "ok":
                if tag == "reference":
                    reference = result
                result["compatibility"] = (
                    compatibility(reference["outputs"], result["outputs"])
                    if reference
                    else {"passed": False, "reason": "reference failed"}
                )
                # Avoid duplicating fixture outputs in the overview; candidate files retain them.
                snapshot(output_path, result)
                result = {key: value for key, value in result.items() if key not in ("outputs", "timings")}
            results.append(result)
            print(f"  {result['status']} p50={result.get('p50_ms')} rss={result.get('peak_rss_mb')}", flush=True)
    recommendations = {}
    for item in selected:
        eligible = [
            row
            for row in results
            if row.get("model") == item["name"]
            and row.get("status") == "ok"
            and row.get("compatibility", {}).get("passed")
            and row.get("actual_device") == "cpu"
        ]
        if eligible:
            fastest = min(row["p50_ms"] for row in eligible)
            # Prefer lower memory/thread use when within 10% of the fastest measured median.
            near_best = [row for row in eligible if row["p50_ms"] <= fastest * 1.1]
            best = min(near_best, key=lambda row: (row["peak_rss_mb"], row["settings"]["threads"]))
            recommendations[item["name"]] = {
                "candidate": best["candidate"],
                "settings": best["settings"],
                "p50_ms": best["p50_ms"],
                "peak_rss_mb": best["peak_rss_mb"],
            }
    report = {
        "schema": 1,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "hardware": hardware(),
        "preset": args.preset,
        "repeats": repeats,
        "fixture_sha256": hashlib.sha256(json.dumps(fixtures(args.preset), sort_keys=True).encode()).hexdigest(),
        "results": results,
        "recommendations": recommendations,
        "limitations": "Synthetic numerical comparison; no Windows or GPU claim without a matching measured row. Recommendations are host-specific.",
    }
    snapshot(directory / "summary.json", report)
    snapshot(STATE / "reports" / "latest.json", report)
    print(f"Report: {directory / 'summary.json'}", flush=True)
    return report


def main() -> Any:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="all")
    parser.add_argument("--config", type=pathlib.Path, default=DEFAULT_CONFIG)
    parser.add_argument("--preset", choices=("quick", "full"), default="quick")
    parser.add_argument("--devices", nargs="+", choices=("cpu", "cuda"), default=["cpu", "cuda"])
    parser.add_argument("--repeats", type=int)
    parser.add_argument("--candidate-timeout", type=int, default=240)
    parser.add_argument("--release-port", type=int)
    parser.add_argument("--item", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    if args.item:
        run_worker(args)
    else:
        sweep(args)


if __name__ == "__main__":
    main()
