"""Replay synthetic native proposals and optionally call real Runtime validators."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
from fullcycle_bridge.native_gui_proposal import (  # noqa: E402
    NativeProposalError,
    compile_native_response,
    context_digest,
)
from scripts.probe_local_gui_executor_v2 import canonical, digest  # noqa: E402

REPORT = ROOT / "baseline/native-gui-proposal-adapter-v1.json"
RUNTIME_COMMIT = "0237f3104a1aeb9263627782df4c3fadc7e6ffe0"
RUNTIME_SOURCES = {
    "src/computer_use_agent/grounding.py": "92e77266a850a8c502532e0877223df45afee0b655114f126fc3a657f578d3c9",
    "src/computer_use_agent/tool_registry.py": "17104b988f29c1871d608de08ed26fa3141bf85307fe4c227bcf223af50e2c6a",
    "src/computer_use_agent/types.py": "124c213b9c7203afacfe00759580452aa99cee98104d33ef139a9d28df05daf4",
}
INPUTS = [
    "configs/local_gui_executor_probe_v2.json",
    "baseline/local-gui-executor-probe-v2.json",
    "baseline/gui-owl-lora-pilot-v1.json",
]


def contexts():
    config = json.loads((ROOT / INPUTS[0]).read_text(encoding="utf-8"))
    targets = [
        ("Address bar", "edit"),
        ("Search articles", "button"),
        ("Document page", "edit"),
        ("Save", "button"),
        ("Save", "button"),
        ("Document page", "edit"),
        ("Delete account", "button"),
        ("Print", "button"),
    ]
    result = {}
    for i, case in enumerate(c for c in config["cases"] if c["group"] == "visual"):
        name, role = targets[i]
        controls = [
            dict(
                ref="ref_90",
                name="Unrelated toolbar",
                role="button",
                enabled=True,
                visible=True,
                bounds=[0, 0, 16, 16],
            )
        ]
        if case["bbox"] is not None:
            controls.append(
                dict(
                    ref=f"ref_{i + 1}",
                    name=name,
                    role=role,
                    enabled=True,
                    visible=True,
                    bounds=case["bbox"],
                )
            )
        result[case["id"]] = dict(
            version=1,
            request_id=f"native-{case['id']}",
            target_scope="314",
            current_epoch=7,
            runtime_generation=3,
            target=dict(name=name, role=role),
            observation=dict(
                scope="314",
                epoch=7,
                foreground_scope="314",
                window_bounds=[0, 0, case["width"], case["height"]],
                frame=dict(
                    sha256=digest(ROOT / case["image"]),
                    width=case["width"],
                    height=case["height"],
                    coordinate_space="primary_screen_pixels",
                ),
                controls=controls,
            ),
        )
    return result


def reply(context, raw):
    return dict(
        request_id=context["request_id"],
        context_digest=context_digest(context),
        raw_output=raw,
    )


def retained_outputs():
    prior = json.loads((ROOT / INPUTS[1]).read_text(encoding="utf-8"))
    pilot = json.loads((ROOT / INPUTS[2]).read_text(encoding="utf-8"))
    streams = {k: v["events_text"] for k, v in prior["candidates"].items()}
    streams["gui-owl-lora"] = pilot["runs"]["after"]["events_text"]
    return {
        name: [
            e
            for line in raw.splitlines()
            if (e := json.loads(line))["event"] == "case_completed"
            and e["group"] == "visual"
        ]
        for name, raw in streams.items()
    }


def replay():
    views = contexts()
    cases = []
    for name, rows in retained_outputs().items():
        for row in rows:
            context = views[row["id"]]
            proposal = compile_native_response(
                context, context, reply(context, row["raw_output"])
            )
            cases.append(
                dict(
                    candidate=name,
                    id=row["id"],
                    context=context,
                    raw_output=row["raw_output"],
                    proposal=proposal.to_dict(),
                )
            )
    # Expected compiler failures are controls, never additional model attempts.
    source = cases[0]
    negatives = []
    for kind in [
        "stale",
        "new_frame",
        "new_epoch",
        "new_generation",
        "new_window",
        "wrong_reply",
        "background",
        "overlap",
        "wrong_target",
        "disabled",
        "hidden",
        "edge",
        "success_claim",
    ]:
        issued = copy.deepcopy(source["context"])
        current = copy.deepcopy(issued)
        raw = source["raw_output"]
        if kind == "stale":
            issued["observation"]["epoch"] -= 1
        elif kind == "new_frame":
            current["observation"]["frame"]["sha256"] = "0" * 64
        elif kind == "new_epoch":
            current["current_epoch"] += 1
        elif kind == "new_generation":
            current["runtime_generation"] += 1
        elif kind == "new_window":
            current["target_scope"] = current["observation"]["scope"] = "315"
        elif kind == "background":
            issued["observation"]["foreground_scope"] = "315"
        elif kind == "overlap":
            issued["observation"]["controls"].append(
                dict(
                    issued["observation"]["controls"][1],
                    ref="ref_100",
                    name="Overlapping popup",
                )
            )
        elif kind == "wrong_target":
            issued["target"]["name"] = "Different target"
        elif kind in {"disabled", "hidden"}:
            issued["observation"]["controls"][1][
                "enabled" if kind == "disabled" else "visible"
            ] = False
        elif kind == "edge":
            raw = '<tool_call>{"name":"computer_use","arguments":{"action":"left_click","coordinate":[1000,200]}}</tool_call>'
        elif kind == "success_claim":
            raw = '<tool_call>{"name":"computer_use","arguments":{"action":"terminate","status":"success"}}</tool_call>'
        if not kind.startswith("new_"):
            current = copy.deepcopy(issued)
        response = reply(issued, raw)
        if kind == "wrong_reply":
            response["request_id"] = "other-request"
        try:
            compile_native_response(issued, current, response)
        except NativeProposalError as exc:
            negatives.append(dict(id=kind, error=str(exc)))
        else:
            raise ValueError(f"Negative unexpectedly accepted: {kind}")
    files = INPUTS + [
        "src/fullcycle_bridge/native_gui_proposal.py",
        "scripts/validate_native_gui_proposal.py",
    ]
    files += sorted(
        {
            c["image"]
            for c in json.loads((ROOT / INPUTS[0]).read_text())["cases"]
            if c["group"] == "visual"
        }
    )
    return dict(
        id="FC-MVP-002-native-gui-proposal-adapter-v1",
        sources={p: digest(ROOT / p) for p in files},
        cases=cases,
        negative_controls=negatives,
        click_proposals=sum(c["proposal"]["tool"] == "click" for c in cases),
        stop_proposals=sum(c["proposal"]["tool"] is None for c in cases),
        model_loaded=False,
        desktop_executed=False,
        runtime_authorization_checked=False,
        limit="Retained model outputs plus synthetic UIA boxes derived from known visual fixtures; not a live observation or independent target-quality test.",
    )


def conformance(runtime_root, report):
    commit = subprocess.check_output(
        ["git", "-C", str(runtime_root), "rev-parse", "HEAD"], text=True
    ).strip()
    sources = {p: digest(runtime_root / p) for p in RUNTIME_SOURCES}
    if commit != RUNTIME_COMMIT or sources != RUNTIME_SOURCES:
        raise ValueError("Runtime pin drift")
    sys.path.insert(0, str(runtime_root / "src"))
    from computer_use_agent.grounding import GroundingError, GroundingState
    from computer_use_agent.tool_registry import get_tool_spec, validate_tool_arguments
    from computer_use_agent.types import (
        CallIdentity,
        DispatchCertainty,
        ToolCall,
        ToolResult,
        ToolResultStatus,
    )

    results = []
    for item in report["cases"]:
        proposal = item["proposal"]
        if proposal["tool"] is None:
            continue
        context = item["context"]
        text = "\n".join(
            f"{c['ref']} | {c['role']}"
            for c in context["observation"]["controls"]
            if c["visible"]
        )
        observation = ToolResult(
            CallIdentity("native_probe", "observe", "snapshot"),
            "ui_snapshot",
            ToolResultStatus.SUCCESS,
            DispatchCertainty.DISPATCHED,
            sanitized_text=text,
        )
        state = GroundingState().observe(
            observation,
            generation=context["runtime_generation"],
            epoch=context["current_epoch"],
        )
        call = ToolCall(
            CallIdentity(
                "native_probe", "propose", f"{item['candidate']}-{item['id']}"
            ),
            proposal["tool"],
            proposal["arguments"],
        )
        validate_tool_arguments(call.name, call.arguments)
        spec = get_tool_spec(call.name)
        state.validate(call, spec, generation=context["runtime_generation"])
        rejected = []
        for name, guard, generation in [
            ("invalidated", state.invalidate(), 3),
            ("new_generation", state, 4),
            (
                "unobserved_ref",
                GroundingState(generation=3, observation_epoch=7, has_observation=True),
                3,
            ),
        ]:
            try:
                guard.validate(call, spec, generation=generation)
            except GroundingError as exc:
                rejected.append(dict(id=name, error=str(exc)))
            else:
                raise ValueError("Runtime negative accepted")
        results.append(
            dict(
                candidate=item["candidate"],
                id=item["id"],
                schema_valid=True,
                grounding_valid=True,
                rejected=rejected,
            )
        )
    return dict(
        commit=subprocess.check_output(
            ["git", "-C", str(runtime_root), "rev-parse", "HEAD"], text=True
        ).strip(),
        sources={
            p: digest(runtime_root / p)
            for p in [
                "src/computer_use_agent/grounding.py",
                "src/computer_use_agent/tool_registry.py",
                "src/computer_use_agent/types.py",
            ]
        },
        cases=results,
        dispatch_count=0,
        synthetic_observations_only=True,
    )


def check_runtime_receipt(report):
    expected = dict(
        commit=RUNTIME_COMMIT,
        sources=RUNTIME_SOURCES,
        dispatch_count=0,
        synthetic_observations_only=True,
        cases=[
            dict(
                candidate=c["candidate"],
                id=c["id"],
                schema_valid=True,
                grounding_valid=True,
                rejected=[
                    dict(id="invalidated", error="GROUNDING_REQUIRED"),
                    dict(id="new_generation", error="MCP_GENERATION_CHANGED"),
                    dict(id="unobserved_ref", error="GROUNDING_REQUIRED"),
                ],
            )
            for c in report["cases"]
            if c["proposal"]["tool"] == "click"
        ],
    )
    if report["runtime"] != expected:
        raise ValueError("Runtime receipt drift")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit-tests", action="store_true")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.unit_tests:
        result = unittest.TextTestRunner(verbosity=1).run(
            unittest.defaultTestLoader.loadTestsFromName(
                "tests.test_native_gui_proposal"
            )
        )
        if not result.wasSuccessful():
            raise SystemExit(1)
    if args.check or args.write_report or args.runtime_root:
        result = replay()
        if args.runtime_root:
            result["runtime"] = conformance(args.runtime_root, result)
            check_runtime_receipt(result)
        if args.write_report:
            if args.runtime_root is None:
                parser.error("--write-report requires --runtime-root")
            REPORT.write_bytes(canonical(result))
        if args.check:
            stored = json.loads(REPORT.read_text(encoding="utf-8"))
            check_runtime_receipt(stored)
            if args.runtime_root is None:
                stored.pop("runtime")
            if result != stored:
                raise ValueError("Retained report drift")
        print(
            json.dumps(
                {
                    "valid": True,
                    "retained_outputs": len(result["cases"]),
                    "clicks": result["click_proposals"],
                    "stops": result["stop_proposals"],
                    "adapter_negatives": len(result["negative_controls"]),
                    "runtime_checked_now": bool(args.runtime_root),
                    "desktop_executed": False,
                }
            )
        )
