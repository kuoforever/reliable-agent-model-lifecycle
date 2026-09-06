"""Recompute the retained local screen with the actual read-only Runtime validator."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def review(runtime_root: Path) -> dict:
    from scripts.probe_local_desktop_readiness import (
        canonical,
        digest,
        messages_for,
        score,
    )

    artifact = ROOT / "baseline/local-desktop-readiness-probe-v1.json"
    bundle = json.loads(artifact.read_text(encoding="utf-8"))
    suite_path = ROOT / "configs/local_desktop_readiness_probe_v1.json"
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    sys.path.insert(0, str(runtime_root / "src"))
    from computer_use_agent.tool_registry import get_tool_spec, validate_tool_arguments
    from computer_use_agent.types import to_json_value

    def require(condition: bool, message: str) -> None:
        if not condition:
            raise ValueError(message)

    require(set(bundle["candidates"]) == {"base", "adapter"}, "candidate coverage")
    frozen_model = json.loads(
        (
            ROOT / "baseline/mm003-qwen2.5-vl-3b-qlora-sft-v2-training-run.json"
        ).read_text()
    )
    expected_model = {
        item["path"]: item["sha256"].removeprefix("sha256:")
        for item in frozen_model["model"]["files"]
    }
    table = {}
    for candidate, entry in bundle["candidates"].items():
        plan, report, rows = entry["plan"], entry["report"], entry["rows"]
        require(plan["model_files"] == expected_model, "frozen base identity")
        require(
            plan["suite"] == suite and plan["suite_sha256"] == digest(suite_path),
            "suite drift",
        )
        require(
            plan["script_sha256"]
            == digest(ROOT / "scripts/probe_local_desktop_readiness.py"),
            "harness drift",
        )
        require(
            plan["runtime_tool_registry_sha256"]
            == digest(runtime_root / "src/computer_use_agent/tool_registry.py"),
            "Runtime schema drift",
        )
        require(
            hashlib.sha256(canonical(plan)).hexdigest() == report["plan_sha256"],
            "plan receipt",
        )
        raw = entry["outputs_jsonl"].encode("utf-8")
        require(
            [json.loads(line) for line in raw.decode().splitlines()] == rows,
            "raw output projection",
        )
        require(
            hashlib.sha256(raw).hexdigest() == report["outputs_sha256"],
            "output receipt",
        )
        require(
            [r["id"] for r in rows] == [c["id"] for c in suite["cases"]],
            "case order/coverage",
        )
        require(
            report["candidate"] == plan["candidate"] == candidate, "candidate identity"
        )
        schemas = {
            name: to_json_value(get_tool_spec(name).input_schema)
            for name in plan["tool_schemas"]
        }
        require(schemas == plan["tool_schemas"], "current Runtime schemas")
        groups = {
            g: {"count": 0, "normalized_task_pass": 0, "strict_task_pass": 0}
            for g in {c["group"] for c in suite["cases"]}
        }
        for case, row in zip(suite["cases"], rows):
            require(row["group"] == case["group"], "group identity")
            require(row["generated_tokens"] == len(row["token_ids"]), "token count")
            stored = plan["messages"][case["id"]]
            reconstructed = messages_for(case, schemas)
            require(len(stored) == 2 and stored[0] == reconstructed[0], "system prompt")
            require(
                stored[1]["role"] == "user"
                and json.loads(stored[1]["content"])
                == json.loads(reconstructed[1]["content"]),
                "semantic prompt projection",
            )
            if case["group"] == "executor":
                validate_tool_arguments(
                    case["expected"]["tool"], case["expected"]["arguments"]
                )
            rescored = score(case, row["raw_output"], validate_tool_arguments)
            require(rescored == row["score"], "score drift")
            group = groups[row["group"]]
            group["count"] += 1
            group["normalized_task_pass"] += int(bool(rescored["task_pass"]))
            group["strict_task_pass"] += int(bool(rescored.get("strict_task_pass")))
        require(
            groups == report["groups"] and report["case_count"] == 12, "aggregate drift"
        )
        table[candidate] = groups
    first, second = (bundle["candidates"][c]["plan"] for c in ["base", "adapter"])
    require(
        first["adapter_files"] == second["adapter_files"], "paired Adapter identity"
    )
    for key in [
        "model_files",
        "messages",
        "tool_schemas",
        "dependencies",
        "dtype",
        "attention",
        "seed",
        "max_new_tokens",
        "max_input_tokens",
        "do_sample",
    ]:
        require(first[key] == second[key], "paired control drift: " + key)
    return {
        "valid": True,
        "candidate_count": 2,
        "case_count": 24,
        "groups": table,
        "model_loaded": False,
        "desktop_executed": False,
        "limit": "recomputes retained hashes, prompts and scores; does not attest execution or rehash current model payloads",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True, type=Path)
    print(json.dumps(review(parser.parse_args().runtime_root)))
