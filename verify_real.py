"""Real checkpoint forward-pass verification, runnable without network sockets."""
import argparse
import json
import logging
import sys
import time

from common import ROOT, config, preflight
from manage import SMOKE
from worker import Engine

parser = argparse.ArgumentParser()
parser.add_argument("model")
args = parser.parse_args()
item = config(ROOT / "config.toml")[args.model]
preflight(item)
sys.path.insert(0, item["source"])
sys.path.extend(item["dependency_paths"])
import os
os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", USE_TF="0", TOKENIZERS_PARALLELISM="false")
logging.basicConfig(level=logging.INFO)
item["device"] = "cpu"
engine = Engine(item)
started = time.monotonic()
engine.lock.acquire()
result = engine.infer(SMOKE, "real-smoke")
assert set(result["answers"]) == set(SMOKE["questions"])
for qid, question in SMOKE["questions"].items():
    answer = result["answers"][qid]
    assert answer["type"] == question["type"]
    if answer["type"] == "noul":
        assert 0 <= answer["noul"] <= 1
    else:
        assert abs(sum(answer["probabilities"].values()) - 1) < 0.001
print(json.dumps({"model": args.model, "seconds_including_load": time.monotonic() - started,
                  "result": result}, ensure_ascii=False, indent=2))
if item["kind"] == "laya":
    long_body = {"state": SMOKE["state"] * 160, "questions": {"refund": SMOKE["questions"]["refund"]}}
    engine.lock.acquire()
    engine.item["strict_jev"] = False
    long_result = engine.infer(long_body, "real-long-smoke")
    assert long_result["usage"]["windows"] > 1
    assert not long_result["usage"].get("truncated")
    print(json.dumps({"long_input_usage": long_result["usage"]}, indent=2))
engine.unload()
assert engine.model is None
