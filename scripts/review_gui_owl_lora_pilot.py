"""Model-free replay of local LoRA pilot evidence; never loads model weights."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_gui_owl_lora_pilot import CONFIG, build, examples  # noqa: E402
from scripts.probe_local_gui_executor_v2 import canonical, digest, score, summarize  # noqa: E402
from scripts.run_gui_owl_lora_pilot import receipts  # noqa: E402

OUTPUT = ROOT / "baseline/gui-owl-lora-pilot-v1.json"


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def review(bundle):
    cfg = json.loads(CONFIG.read_text())
    require(cfg == build(), "data reproduction")
    require(
        set(bundle["runs"]) == {"preflight", "before", "train", "after"},
        "run inventory",
    )
    old = json.loads((ROOT / "configs/local_gui_executor_probe_v2.json").read_text())[
        "cases"
    ]
    cases = cfg["splits"]["test"] + old
    plans, events = {}, {}
    for name, run in bundle["runs"].items():
        plan = plans[name] = run["plan"]
        ev = events[name] = [
            json.loads(line) for line in run["events_text"].splitlines()
        ]
        require(
            hashlib.sha256(run["events_text"].encode()).hexdigest()
            == run["events_sha256"],
            "events digest",
        )
        require(plan["sources"] == receipts(), "source drift")
        require(plan["config_sha256"] == digest(CONFIG), "config drift")
        require(plan["training"] == cfg["training"], "training config")
        require(
            plan["model_id"] == cfg["model_id"] and plan["revision"] == cfg["revision"],
            "model identity",
        )
        require(
            plan["mode"] == (name if name in {"preflight", "train"} else "eval"), "mode"
        )
        require(ev[-1]["event"] == "completed", "incomplete run")
        require(
            ev[-1]["plan_sha256"] == hashlib.sha256(canonical(plan)).hexdigest(),
            "plan digest",
        )
        require(
            0
            < ev[-1]["peak_allocated_bytes"]
            <= cfg["training"]["max_allocated_bytes"],
            "memory cap",
        )
        require(ev[-1]["elapsed_seconds"] <= cfg["training"]["max_seconds"], "time cap")
        require(
            all(
                math.isfinite(e["elapsed_seconds"]) and e["elapsed_seconds"] >= 0
                for e in ev
            ),
            "finite clock",
        )
        require(
            [e["elapsed_seconds"] for e in ev]
            == sorted(e["elapsed_seconds"] for e in ev),
            "event order",
        )
    for plan in plans.values():
        require(plan["model_files"] == plans["before"]["model_files"], "same base")
        require(
            plan["environment"] == plans["before"]["environment"], "same environment"
        )
    prior = json.loads(
        (ROOT / "baseline/local-gui-executor-probe-v2.json").read_text(encoding="utf-8")
    )
    prior_files = prior["candidates"]["gui-owl"]["plan"]["model_files"]
    require(
        all(
            plans["before"]["model_files"].get(name) == receipt["sha256"]
            for name, receipt in prior_files.items()
        ),
        "prior model provenance",
    )
    for name in ["preflight", "before", "train"]:
        require(plans[name]["adapter_files"] is None, "unexpected initial adapter")
    for name in ["preflight", "train"]:
        ev = events[name]
        steps = 1 if name == "preflight" else cfg["training"]["steps"]
        grammar = [
            "load_started",
            "load_completed",
            "adapter_configured",
            "tokenized",
        ] + ["optimizer_step"] * steps
        if name == "train":
            grammar += ["validation_loss", "adapter_saved"]
        require([e["event"] for e in ev] == grammar + ["completed"], "training grammar")
        trainable = ev[2]["trainable"]
        require(
            len(trainable) == 144 and ev[2]["trainable_parameters"] == 2949120,
            "adapter size",
        )
        require(
            all(
                "lora_" in n
                and ".language_model.layers." in n
                and v["dtype"] == "torch.float32"
                for n, v in trainable.items()
            ),
            "trainable boundary",
        )
        pool = examples(997, 1)[:4] if name == "preflight" else cfg["splits"]["train"]
        allowed = {c["id"] for c in pool}
        require(
            ev[3]["records"] == len(pool)
            and ev[3]["max_tokens"] <= cfg["training"]["max_tokens"],
            "tokenization",
        )
        require(
            len(ev[3]["supervised_tokens"]) == len(pool)
            and min(ev[3]["supervised_tokens"]) > 0,
            "supervision",
        )
        for step, row in enumerate(ev[4 : 4 + steps], 1):
            require(
                row["step"] == step
                and len(row["ids"]) == cfg["training"]["accumulation"],
                "optimizer step",
            )
            require(set(row["ids"]) <= allowed, "training split leakage")
            require(
                math.isfinite(row["loss"])
                and row["loss"] >= 0
                and math.isfinite(row["gradient_norm"])
                and row["gradient_norm"] > 0,
                "finite training",
            )
        if name == "train":
            seen = Counter(
                identity for row in ev[4 : 4 + steps] for identity in row["ids"]
            )
            require(
                seen == Counter({identity: 2 for identity in allowed}),
                "two training epochs",
            )
            require(
                ev[-3]["count"] == 12 and math.isfinite(ev[-3]["loss"]), "validation"
            )
            require(
                ev[-2]["files"] == plans["after"]["adapter_files"],
                "fresh loaded saved adapter",
            )
    results = {}
    paired = {}
    for name in ["before", "after"]:
        ev = events[name]
        require(
            [e["event"] for e in ev]
            == ["load_started", "load_completed", "generation_configured"]
            + [kind for _ in cases for kind in ["case_started", "case_completed"]]
            + ["evaluation_completed", "completed"],
            "evaluation grammar",
        )
        effective = ev[2]["effective"]
        require(
            effective["do_sample"] is False
            and effective["num_beams"] == 1
            and effective["max_new_tokens"] == 192,
            "greedy config",
        )
        rows = []
        for i, case in enumerate(cases):
            started, row = ev[3 + 2 * i : 5 + 2 * i]
            require(started["id"] == row["id"] == case["id"], "case identity")
            require(row["group"] == case["group"], "case group")
            require(row["cohort"] == ("fresh" if i < 24 else "regression"), "cohort")
            require(row["score"] == score(case, row["raw_output"]), "score drift")
            require(
                len(row["token_ids"]) <= 192 and 0 < row["input_tokens"] <= 4096,
                "generation budget",
            )
            require(
                math.isfinite(row["generation_seconds"])
                and row["generation_seconds"] >= 0,
                "latency",
            )
            if name == "before":
                paired[case["id"]] = row["rendered_prompt"]
            else:
                require(
                    row["rendered_prompt"] == paired[case["id"]],
                    "paired prompt mismatch",
                )
            rows.append(row)
        cohorts = {
            k: summarize([r for r in rows if r["cohort"] == k])
            for k in ["fresh", "regression"]
        }
        require(cohorts == ev[-2]["cohorts"], "aggregate drift")
        results[name] = dict(
            cohorts=cohorts,
            family_exact={
                f: sum(
                    r["score"]["task_pass"]
                    for r, c in zip(rows[:24], cases[:24])
                    if c["family"] == f
                )
                for f in sorted({c["family"] for c in cases[:24]})
            },
        )
    before = results["before"]["cohorts"]["fresh"]["contract"]["task_pass"]
    after = results["after"]["cohorts"]["fresh"]["contract"]["task_pass"]
    passed = (
        after >= cfg["rubric"]["fresh_exact_min"]
        and after - before >= cfg["rubric"]["fresh_gain_min"]
        and results["after"]["cohorts"]["regression"]["visual"]["task_pass"]
        >= cfg["rubric"]["visual_exact_min"]
    )
    return dict(
        results=results,
        fresh_gain=after - before,
        pilot_threshold_passed=passed,
        desktop_executed=False,
        runtime_eligible=False,
        limitations="Synthetic same-family contract adaptation; eight known visual regression tasks; no live GUI, planning or summary quality evaluation.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--collect", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--adapter-root", type=Path)
    parser.add_argument("--unit-tests", action="store_true")
    args = parser.parse_args()
    if args.unit_tests:
        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromName(
                "tests.test_gui_owl_lora_pilot"
            )
        )
        if not result.wasSuccessful():
            raise SystemExit(1)
    if args.collect:
        bundle = {"runs": {}}
        for name in ["preflight", "before", "train", "after"]:
            folder = args.collect / name
            raw = (folder / "events.jsonl").read_text(encoding="utf-8")
            bundle["runs"][name] = dict(
                plan=json.loads((folder / "plan.json").read_text()),
                events_text=raw,
                events_sha256=hashlib.sha256(raw.encode()).hexdigest(),
            )
        bundle["summary"] = review(bundle)
        OUTPUT.write_bytes(canonical(bundle))
    if args.check or args.adapter_root:
        bundle = json.loads(OUTPUT.read_text(encoding="utf-8"))
        require(review(bundle) == bundle["summary"], "summary drift")
        if args.adapter_root:
            require(
                {
                    p.name: digest(p)
                    for p in sorted(args.adapter_root.glob("*"))
                    if p.is_file()
                }
                == bundle["runs"]["after"]["plan"]["adapter_files"],
                "adapter file drift",
            )
        print(json.dumps(bundle["summary"], indent=2))
