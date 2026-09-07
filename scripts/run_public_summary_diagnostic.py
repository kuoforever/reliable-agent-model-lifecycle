"""One v2-aware diagnostic on the pinned reference; no desktop or network API."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.probe_public_source_summary import (  # noqa: E402
    REASONS, STAGES, SYSTEM, parse_request, render_brief, sha, strict_object,
)

WORKER_SHA = "b5be14217184010aad8a2f113d6f83213cb780e5a801a821be0ea9c78fad4b40"
SOURCE_SHA = "c3cf519cadef0e1f55c6457c7151d67553b8c87f70d79a128373dd78d9d70a1a"
REQUEST_ID = "public-source-summary-stage-20260907"


def validate_response(response, request, exit_code):
    if type(response) is not dict or type(response.get("version")) is not int or response["version"] != 2:
        raise ValueError("RESPONSE_VERSION")
    if response.get("status") == "ERROR":
        if (exit_code != 1 or set(response) != {"version", "status", "code", "reason", "stage", "model_requests"}
                or response["code"] != "SUMMARY_WORKER_FAILED"
                or type(response["reason"]) is not str or response["reason"] not in REASONS | {"UNCLASSIFIED"}
                or type(response["stage"]) is not str or response["stage"] not in STAGES
                or type(response["model_requests"]) is not int or response["model_requests"] not in (0, 1)):
            raise ValueError("ERROR_RESPONSE")
        return
    fixed = dict(version=2, status="OK", request_id=request["request_id"],
                 source_sha256=request["source_sha256"], model_requests=1,
                 model_id="mPLUG/GUI-Owl-1.5-4B-Instruct",
                 revision="3f061c2c562cc860c42bf32542a70e07a7ff4840",
                 adapter_sha256="3654fc21a2cea688754b800f9b10a49ae5e931f6ceb7eec080bfd83931fd0445",
                 execution_authorized=False)
    if exit_code != 0 or set(response) != set(fixed) | {"raw_output", "input_tokens", "output_tokens",
                                                       "generation_seconds", "peak_allocated_bytes"}:
        raise ValueError("RESPONSE_FIELDS")
    for key, value in fixed.items():
        if type(response[key]) is not type(value) or response[key] != value:
            raise ValueError("RESPONSE_BINDING")
    for key, cap in [("input_tokens", 4096), ("output_tokens", 384), ("peak_allocated_bytes", 15_000_000_000)]:
        if type(response[key]) is not int or not 0 < response[key] <= cap:
            raise ValueError("RESPONSE_RESOURCE")
    seconds = response["generation_seconds"]
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 60:
        raise ValueError("RESPONSE_RESOURCE")
    if type(response["raw_output"]) is not str or len(response["raw_output"].encode()) > 4096:
        raise ValueError("RESPONSE_OUTPUT")


def run(reference, output, *, invoke=subprocess.run):
    request = parse_request(reference.read_bytes())
    if request["source_sha256"] != SOURCE_SHA:
        raise ValueError("REFERENCE_DRIFT")
    request["request_id"] = REQUEST_ID
    raw_request = json.dumps(request).encode()
    worker = ROOT / "scripts/probe_public_source_summary.py"
    if sha(worker.read_bytes()) != WORKER_SHA:
        raise ValueError("WORKER_DRIFT")
    # Exclusive directory creation consumes this named local attempt before any call.
    output.mkdir(exist_ok=False)
    pins = dict(version=1, request_id=REQUEST_ID, source_sha256=SOURCE_SHA,
                request_sha256=sha(raw_request), worker_sha256=WORKER_SHA,
                parent_sha256=sha(Path(__file__).read_bytes()), system_prompt_sha256=sha(SYSTEM.encode()),
                source_kind="pinned_public_reference_excerpt", reference_access_date="2026-09-07",
                runtime_browser_observation=False, desktop_calls=0, runtime_provider_turns=0,
                side_effects=0, retry_count=0, execution_authorized=False,
                model_admission_changed=False, automatic_fullcycle_export=False)
    (output / "before.json").write_text(json.dumps(pins, indent=2), encoding="utf-8")
    allowed = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA"}
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    receipt = dict(pins, outcome="FAIL", worker_invocations=1, model_requests=None,
                   code="PARENT_UNCLASSIFIED", shape_passed=None, factual_review="NOT_ASSESSABLE")
    try:
        completed = invoke([str(ROOT / "work/gui-owl-lora-env/Scripts/python.exe"), "-I", "-B",
                            str(worker), "--one-reference-summary"], input=raw_request,
                           cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=180, check=False)
        if len(completed.stdout) > 16384:
            raise ValueError("RESPONSE_SIZE")
        response = strict_object(completed.stdout)
        validate_response(response, request, completed.returncode)
        if sha(worker.read_bytes()) != WORKER_SHA:
            raise ValueError("WORKER_DRIFT")
        receipt.update(process_exit_code=completed.returncode, model_requests=response["model_requests"])
        if response["status"] == "ERROR":
            receipt.update(code=response["code"], stage=response["stage"], reason=response["reason"])
        else:
            receipt.update({k: v for k, v in response.items() if k not in {"version", "raw_output", "status"}})
            receipt.update(code="SUMMARY_RETURNED", raw_output_sha256=sha(response["raw_output"].encode()),
                           factual_review="PENDING")
            (output / "response.local.json").write_text(json.dumps(response), encoding="utf-8")
            try:
                brief = render_brief(response["raw_output"])
                receipt.update(outcome="PASS", shape_passed=True, brief_characters=len(brief),
                               brief_sha256=sha(brief.encode()))
            except ValueError:
                receipt.update(shape_passed=False, code="SUMMARY_SHAPE_REJECTED")
    except subprocess.TimeoutExpired:
        receipt.update(code="WORKER_TIMEOUT")
    except (ValueError, OSError):
        receipt.update(code="PARENT_RESPONSE_REJECTED")
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--one-stage-diagnostic", action="store_true", required=True)
    parser.parse_args()
    receipt = run(ROOT / "work/public-source-summary-20260907/request.json",
                  ROOT / "work/public-source-summary-stage-20260907")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["outcome"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
