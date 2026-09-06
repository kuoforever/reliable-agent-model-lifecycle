"""Collect and independently rescore retained local GUI probe evidence, model-free."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.probe_local_gui_executor_v2 import (  # noqa: E402
    CONFIG,
    canonical,
    messages_for,
    score,
    source_receipts,
    summarize,
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def review(bundle):
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    require(set(bundle["candidates"]) == set(config["candidates"]), "candidate set")
    table = {}
    environments = []
    for name, candidate in bundle["candidates"].items():
        plan, report = candidate["plan"], candidate["report"]
        raw_events = candidate["events_text"]
        require(plan["candidate"] == name == report["candidate"], "candidate identity")
        require(plan["model"] == config["candidates"][name], "model identity")
        require(plan["config"] == config, "config drift")
        require(plan["sources"] == source_receipts(config), "source drift")
        require(
            plan["messages"] == {c["id"]: messages_for(c) for c in config["cases"]},
            "prompt drift",
        )
        require(
            hashlib.sha256(canonical(plan)).hexdigest() == report["plan_sha256"],
            "plan hash",
        )
        require(
            hashlib.sha256(raw_events.encode()).hexdigest() == report["events_sha256"],
            "events hash",
        )
        events = [json.loads(line) for line in raw_events.splitlines()]
        require(
            [r["event"] for r in events]
            == [
                "load_started",
                "loaded",
                "generation_configured",
                "smoke_started",
                "smoke_completed",
            ]
            + [
                kind
                for _ in config["cases"]
                for kind in ["case_started", "case_completed"]
            ],
            "event grammar",
        )
        rows = []
        effective = events[2]
        require(
            effective["effective"]["do_sample"] is False
            and effective["effective"]["num_beams"] == 1
            and effective["use_model_defaults"] is False
            and effective["do_sample_kwarg"] is False,
            "effective greedy configuration",
        )
        for index, case in enumerate(config["cases"]):
            start, row = events[5 + 2 * index : 7 + 2 * index]
            require(start["id"] == row["id"] == case["id"], "case identity")
            require(row["group"] == case["group"], "case group")
            require(row["score"] == score(case, row["raw_output"]), "score drift")
            require(
                len(row["token_ids"])
                == row["generated_tokens"]
                <= config["generation"]["max_new_tokens"],
                "output budget",
            )
            require(
                0 < row["input_tokens"] <= config["generation"]["max_input_tokens"],
                "input budget",
            )
            require(row["generation_seconds"] >= 0, "latency")
            rows.append(row)
        require(report["case_count"] == len(rows) == 16, "case count")
        require(report["groups"] == summarize(rows), "aggregate drift")
        require(
            report["completed"] is True
            and report["model_evaluated"] is True
            and report["synthetic_images_only"] is True,
            "execution claims",
        )
        for key in [
            "desktop_executed",
            "runtime_authorization_checked",
            "serving_eligible",
        ]:
            require(report[key] is False, "overclaim")
        require(
            report["resource_caps_pass"]
            == (
                report["peak_allocated_bytes"]
                <= config["limits"]["peak_allocated_bytes"]
                and report["total_seconds"] <= config["limits"]["candidate_seconds"]
            ),
            "resource gate",
        )
        for receipt in [r for r in bundle["download_receipts"] if r["model"] == name]:
            retained = plan["model_files"][receipt["file"]]
            require(
                receipt["sha256"] == retained["sha256"]
                and receipt["bytes"] == retained["bytes"],
                "transport/model mismatch",
            )
        environments.append(plan["environment"])
        positive = [
            r
            for r, c in zip(rows, config["cases"])
            if c["group"] == "visual" and c["bbox"] is not None
        ]
        absent = [
            r
            for r, c in zip(rows, config["cases"])
            if c["group"] == "visual" and c["bbox"] is None
        ]
        table[name] = {
            "groups": report["groups"],
            "positive_visual_hits": sum(r["score"]["task_pass"] for r in positive),
            "positive_visual_count": len(positive),
            "absent_target_correct_stops": sum(r["score"]["task_pass"] for r in absent),
            "absent_target_count": len(absent),
            "peak_allocated_bytes": report["peak_allocated_bytes"],
            "load_seconds": report["load_seconds"],
        }
        from fullcycle_bridge.local_gui_executor import (
            ExecutorContractError,
            compile_response,
        )

        errors = {}
        for case, row in zip(config["cases"], rows):
            if case["group"] == "contract":
                try:
                    compile_response(
                        case["request"], case["request"], row["raw_output"]
                    )
                except ExecutorContractError as exc:
                    errors[str(exc)] = errors.get(str(exc), 0) + 1
        table[name]["contract_rejection_codes"] = errors
    require(environments[0] == environments[1], "paired environment drift")
    require(len(bundle["download_receipts"]) == 4, "download receipt count")
    excluded = bundle["excluded_attempts"]["gui-owl-v1"]
    require(
        hashlib.sha256(canonical(excluded["plan"])).hexdigest()
        == excluded["report"]["plan_sha256"],
        "excluded plan hash",
    )
    require(
        hashlib.sha256(excluded["events_text"].encode()).hexdigest()
        == excluded["report"]["events_sha256"],
        "excluded events hash",
    )
    require(excluded["included_in_comparison"] is False, "excluded attempt mixing")
    require(
        excluded["plan"]["config"]["cases"] == config["cases"],
        "changed tasks after excluded attempt",
    )
    require(
        excluded["plan"]["messages"]
        == bundle["candidates"]["gui-owl"]["plan"]["messages"],
        "changed prompts after excluded attempt",
    )
    require(
        excluded["plan"]["model_files"]
        == bundle["candidates"]["gui-owl"]["plan"]["model_files"],
        "changed weights after excluded attempt",
    )
    check = bundle["generation_default_check"]
    require(
        check["initial_effective_do_sample"] is True
        and check["corrected_effective_do_sample"] is False
        and check["model_loaded"] is False
        and check["transformers"] == environments[0]["transformers"],
        "configuration check receipt",
    )
    return {
        "valid": True,
        "case_count": 32,
        "results": table,
        "model_loaded": False,
        "desktop_executed": False,
        "limit": "recomputes retained source/prompt/hash/score/event consistency; does not attest execution or rehash present model payloads",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", type=Path)
    parser.add_argument("--unit-tests", action="store_true")
    args = parser.parse_args()
    if args.unit_tests:
        suite = unittest.defaultTestLoader.loadTestsFromName(
            "tests.test_local_gui_probe_v2"
        )
        return int(not unittest.TextTestRunner().run(suite).wasSuccessful())
    if args.collect:
        if args.output is None or args.output.exists():
            parser.error("collection requires a fresh --output")
        bundle = {
            "id": "FC-MVP-002-local-gui-executor-probe-v2",
            "candidates": {},
            "download_receipts": json.loads(
                (args.collect / "download-receipts.json").read_text()
            ),
        }
        for name in ["gui-owl", "qwen"]:
            root = args.collect / "runs" / (name + "-v2")
            bundle["candidates"][name] = {
                "plan": json.loads((root / "plan.json").read_text(encoding="utf-8")),
                "report": json.loads((root / "report.json").read_text()),
                "events_text": (root / "events.jsonl").read_bytes().decode(),
            }
        excluded = args.collect / "runs/gui-owl-v1"
        bundle["excluded_attempts"] = {
            "gui-owl-v1": {
                "plan": json.loads(
                    (excluded / "plan.json").read_text(encoding="utf-8")
                ),
                "report": json.loads((excluded / "report.json").read_text()),
                "events_text": (excluded / "events.jsonl").read_bytes().decode(),
                "included_in_comparison": False,
                "reason": json.loads(CONFIG.read_text())["excluded_prior_attempt"][
                    "reason"
                ],
            }
        }
        bundle["generation_default_check"] = json.loads(
            (args.collect / "generation-default-check.json").read_text()
        )
        result = review(bundle)
        args.output.write_bytes(canonical(bundle))
    elif args.check:
        result = review(json.loads(args.check.read_text(encoding="utf-8")))
    else:
        parser.error("choose --collect, --check, or --unit-tests")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
