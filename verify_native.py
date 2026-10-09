"""Real native model: invalid-input recovery, fresh state, unload and reload."""
import json
from common import DEFAULT_CONFIG, config, preflight, prepare_runtime


def main():
    item = config(DEFAULT_CONFIG)["startlux-0.8b"]
    item.update(device="cpu", startlux_backend="gguf-stdio")
    preflight(item)
    prepare_runtime(item)
    from worker import Engine
    from benchmark import fixtures
    engine = Engine(item)
    try:
        engine.load()
        pid = engine.native_process.pid
    finally:
        engine.unload()
    import subprocess
    with subprocess.Popen([item["native_binary"], item["gguf_file"], "1024", "4", "0"],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                          text=True, encoding="utf-8") as process:
        assert json.loads(process.stdout.readline())["ready"]
        process.stdin.write('{"tokens":[-1],"letters":[1]}\n')
        process.stdin.flush()
        assert "error" in json.loads(process.stdout.readline())
        process.stdin.write('{"tokens":[1,2],"letters":[10,11]}\n')
        process.stdin.flush()
        assert len(json.loads(process.stdout.readline())["logits"]) == 2
        process.stdin.close()
        assert process.wait(timeout=10) == 0
    try:
        engine.load()
        assert engine.native_process.pid != pid
        body = fixtures("quick")[0]["body"]
        engine.lock.acquire()
        first = engine.infer(body, "native-first")
        engine.lock.acquire()
        engine.infer(fixtures("quick")[1]["body"], "native-other-context")
        engine.lock.acquire()
        again = engine.infer(body, "native-state-reset")
        assert first["answers"] == again["answers"], "native state leaked between requests"
        long_body = dict(fixtures("quick")[-1]["body"], max_len=256)
        engine.lock.acquire()
        try:
            engine.infer(long_body, "native-context-limit")
        except ValueError:
            pass
        else:
            raise AssertionError("long input was accepted above configured limit")
        print("PASS: invalid token recovery, context isolation, unload/reload, context bound, Jev three types")
    finally:
        engine.unload()


if __name__ == "__main__":
    main()
