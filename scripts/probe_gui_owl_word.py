"""One experimental Word-editor image proposal; no desktop API."""
from __future__ import annotations

import argparse
import base64
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.probe_local_gui_executor_v2 import VISUAL_SYSTEM, digest  # noqa: E402

MAX_INPUT_BYTES = 12 * 1024 * 1024
MAX_IMAGE_BYTES = 8 * 1024 * 1024


def parse_request(raw):
    if type(raw) is not bytes or len(raw) > MAX_INPUT_BYTES:
        raise ValueError("REQUEST_SIZE")

    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("DUPLICATE_FIELD")
            value[key] = item
        return value

    request = json.loads(raw, object_pairs_hook=unique)
    if type(request) is not dict or set(request) != {
        "version", "request_id", "context_digest", "image_base64",
    }:
        raise ValueError("REQUEST_FIELDS")
    if type(request["version"]) is not int or request["version"] != 1:
        raise ValueError("VERSION")
    for key, pattern in [
        ("request_id", r"[a-z0-9][a-z0-9_-]{0,63}"),
        ("context_digest", r"[0-9a-f]{64}"),
    ]:
        if type(request[key]) is not str or not re.fullmatch(pattern, request[key]):
            raise ValueError("BINDING")
    if type(request["image_base64"]) is not str:
        raise ValueError("IMAGE")
    image = base64.b64decode(request["image_base64"], validate=True)
    if not 0 < len(image) <= MAX_IMAGE_BYTES or not image.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("IMAGE")
    return request, image


def model_files():
    plan = json.loads((ROOT / "baseline/gui-owl-lora-pilot-v1.json").read_text(
        encoding="utf-8"))["runs"]["after"]["plan"]
    model = ROOT / "work/gui-probe-v2/models/gui-owl"
    adapter = ROOT / "work/gui-owl-lora-v1/train/adapter"
    for directory, expected in [(model, plan["model_files"]), (adapter, plan["adapter_files"])]:
        for name, sha in expected.items():
            if Path(name).name != name or digest(directory / name) != sha:
                raise ValueError("MODEL_FILE_MISMATCH")
    return model, adapter, plan


def generate(request, png, count):
    for key in ["HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"]:
        os.environ[key] = "1"
    import importlib.metadata
    import torch
    from PIL import Image
    from peft import PeftModel
    from transformers import AutoProcessor, GenerationConfig, Qwen3VLForConditionalGeneration

    model_path, adapter_path, plan = model_files()
    if any(importlib.metadata.version(n) != v for n, v in plan["environment"].items()):
        raise ValueError("ENVIRONMENT_MISMATCH")
    with Image.open(BytesIO(png)) as opened:
        if opened.format != "PNG" or opened.width * opened.height > 64_000_000:
            raise ValueError("IMAGE_DIMENSIONS")
        image = opened.convert("RGB")
    torch.manual_seed(17)
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.cuda.reset_peak_memory_stats()
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_path, dtype=torch.bfloat16, attn_implementation="sdpa", device_map={"": 0},
        local_files_only=True, trust_remote_code=False,
    )
    model = PeftModel.from_pretrained(
        model, adapter_path, is_trainable=False, local_files_only=True,
    ).eval()
    processor = AutoProcessor.from_pretrained(
        model_path, local_files_only=True, trust_remote_code=False,
    )
    processor.image_processor.size = {"shortest_edge": 65536, "longest_edge": 655360}
    messages = [
        {"role": "system", "content": VISUAL_SYSTEM},
        {"role": "user", "content": [
            {"type": "image", "image": "captured-disposable-word"},
            {"type": "text", "text": "Click inside the main document page editing area in Microsoft Word. Avoid the ribbon, title bar, navigation pane and status bar."},
        ]},
    ]
    prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=[prompt], images=[image], return_tensors="pt").to("cuda")
    tokens_in = inputs.input_ids.shape[1]
    if tokens_in > 4096:
        raise ValueError("INPUT_TOKEN_CAP")
    config = GenerationConfig(
        do_sample=False, num_beams=1, max_new_tokens=192, max_time=45, use_cache=True,
        eos_token_id=model.generation_config.eos_token_id,
        pad_token_id=processor.tokenizer.pad_token_id,
    )
    effective, _ = model._prepare_generation_config(config, use_model_defaults=False, do_sample=False)
    if effective.do_sample or effective.num_beams != 1:
        raise ValueError("GREEDY_CONFIGURATION")
    torch.cuda.synchronize()
    began = time.monotonic()
    count[0] += 1
    with torch.inference_mode():
        output = model.generate(
            **inputs, generation_config=config, use_model_defaults=False, do_sample=False,
        )
    torch.cuda.synchronize()
    elapsed = time.monotonic() - began
    tokens = output[0, tokens_in:].tolist()
    raw = processor.decode(tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    peak = torch.cuda.max_memory_allocated()
    if len(raw.encode()) > 4096 or peak > 15_000_000_000 or elapsed > 60:
        raise ValueError("OUTPUT_RESOURCE_CAP")
    # Rehash the small saved adapter after use; base files were verified before load.
    if any(digest(adapter_path / n) != h for n, h in plan["adapter_files"].items()):
        raise ValueError("ADAPTER_DRIFT")
    return dict(
        version=1, status="OK", request_id=request["request_id"],
        context_digest=request["context_digest"], raw_output=raw, model_requests=count[0],
        model_id=plan["model_id"], revision=plan["revision"],
        adapter_sha256=plan["adapter_files"]["adapter_model.safetensors"],
        image_sha256=hashlib.sha256(png).hexdigest(), input_tokens=tokens_in,
        output_tokens=len(tokens), generation_seconds=elapsed, peak_allocated_bytes=peak,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--one-inert-proposal", action="store_true", required=True)
    parser.parse_args(argv)
    count = [0]
    try:
        request, png = parse_request(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
        result = generate(request, png, count)
    except Exception:
        result = dict(version=1, status="ERROR", code="MODEL_WORKER_FAILED", model_requests=count[0])
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if result["status"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
