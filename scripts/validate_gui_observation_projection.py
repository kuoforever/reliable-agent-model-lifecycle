"""Model-free projection gate with optional real Runtime formatting conformance."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
from fullcycle_bridge.gui_observation_projection import (  # noqa: E402
    ObservationProjectionError,
    inspect_observations,
    project_observation,
)
from fullcycle_bridge.native_gui_proposal import (  # noqa: E402
    NativeProposalError,
    compile_native_response,
    context_digest,
)
from scripts.probe_local_gui_executor_v2 import canonical, digest  # noqa: E402

REPORT = ROOT / "baseline/gui-observation-projection-v1.json"
IMAGE = ROOT / "fixtures/local_gui_probe_v2/word.png"
PIN = "0237f3104a1aeb9263627782df4c3fadc7e6ffe0"
RUNTIME_SOURCES = {
    "src/computer_use_agent/types.py": "124c213b9c7203afacfe00759580452aa99cee98104d33ef139a9d28df05daf4",
    "src/computer_use_mcp/contract.py": "58b40181fd2385c28ca480f3720fefacaa2b203a397261ff32464f79c868995a",
    "src/computer_use_mcp/core.py": "b91825c96ade43816f2b00d6525a990a10653fb2ce34cf3d3daa4496045dced1",
    "src/computer_use_mcp/drivers/windows.py": "024b5bb0f9f24c5a2e7e56be844e6d61e1f07032e6d0044a54cab078fdb599f0",
    "src/computer_use_mcp/server.py": "c2d10eced07b2cbd0c8a92ef7837aa76c8c33611a67a043d30cfe33c1fed2f66",
}


def check_runtime_receipt(value):
    if value != dict(
        commit=PIN,
        sources=RUNTIME_SOURCES,
        session_snapshot_matched=True,
        tool_results_checked=3,
        projection_matched=True,
        driver="synthetic get_tree only",
        desktop_calls=0,
    ):
        raise ValueError("Runtime receipt drift")


def fixture():
    task = dict(
        version=1,
        request_id="projection-control",
        target_scope="314",
        current_epoch=3,
        runtime_generation=7,
        target=dict(name="Document page", role="edit"),
    )
    results = {}
    for epoch, (key, tool, arguments, text) in enumerate(
        [
            ("windows", "list_windows", {}, '* 314 | word.exe | "Synthetic document"'),
            (
                "snapshot",
                "ui_snapshot",
                {"scope": "314"},
                'ref_1 | edit "Document page" | (100,100,200,150) | enabled,focused',
            ),
            ("screenshot", "screenshot", {}, ""),
        ],
        1,
    ):
        results[key] = dict(
            call_id="call-" + key,
            tool=tool,
            status="success",
            dispatch="dispatched",
            generation=7,
            epoch=epoch,
            arguments=arguments,
            text=text,
        )
    image = IMAGE.read_bytes()
    facts = dict(
        binding_digest=inspect_observations(task, results, image)["binding_digest"],
        window_bounds=[0, 0, 1024, 640],
        frame_origin=[0, 0],
        coherent_complete_projection=True,
        control_states={"ref_1": dict(enabled=True, visible=True)},
    )
    return task, results, image, facts


def replay():
    task, results, image, facts = fixture()
    incomplete = project_observation(task, results, image)
    projected = project_observation(task, results, image, facts)
    context = projected["context"]
    raw = '<tool_call>{"name":"computer_use","arguments":{"action":"left_click","coordinate":[195,273]}}</tool_call>'
    proposal = compile_native_response(
        context,
        context,
        dict(
            request_id=task["request_id"],
            context_digest=context_digest(context),
            raw_output=raw,
        ),
    ).to_dict()
    negatives = []
    for name in [
        "wrong_scope",
        "mixed_generation",
        "failed_result",
        "sequence",
        "truncated",
        "incomplete_footer",
        "unknown_role",
        "wrong_binding",
        "wrong_origin",
        "not_coherent",
        "missing_state",
        "wrong_rectangle",
    ]:
        changed = copy.deepcopy(results)
        host = copy.deepcopy(facts)
        if name == "wrong_scope":
            changed["snapshot"]["arguments"]["scope"] = "foreground"
        elif name == "mixed_generation":
            changed["snapshot"]["generation"] = 8
        elif name == "failed_result":
            changed["snapshot"]["status"] = "action_error"
        elif name == "sequence":
            changed["snapshot"]["epoch"] = 3
        elif name == "truncated":
            changed["snapshot"]["text"] += "\n# … 2 more truncated — narrow with find()"
        elif name == "incomplete_footer":
            changed["snapshot"]["text"] += "\n# incomplete: browser tree unavailable"
        elif name == "unknown_role":
            changed["snapshot"]["text"] = changed["snapshot"]["text"].replace(
                "| edit ", "| checkbox "
            )
        elif name == "wrong_binding":
            host["binding_digest"] = "0" * 64
        elif name == "wrong_origin":
            host["frame_origin"] = [-1920, 0]
        elif name == "not_coherent":
            host["coherent_complete_projection"] = False
        elif name == "missing_state":
            host["control_states"] = {}
        elif name == "wrong_rectangle":
            host["window_bounds"] = [0, 0, 110, 110]
        try:
            project_observation(task, changed, image, host)
        except (ObservationProjectionError, NativeProposalError) as exc:
            negatives.append(dict(id=name, error=str(exc)))
        else:
            raise ValueError("negative accepted")
    paths = [
        "src/fullcycle_bridge/gui_observation_projection.py",
        "src/fullcycle_bridge/native_gui_proposal.py",
        "scripts/validate_gui_observation_projection.py",
        IMAGE.relative_to(ROOT).as_posix(),
    ]
    return dict(
        id="FC-MVP-002-gui-observation-projection-v1",
        sources={p: digest(ROOT / p) for p in paths},
        task=task,
        synthetic_results=results,
        synthetic_host_facts=facts,
        incomplete=incomplete,
        projected=projected,
        proposal=proposal,
        negatives=negatives,
        model_loaded=False,
        desktop_executed=False,
        runtime_modified=False,
        limitation="Legacy results alone remain incomplete. Supplementary Host facts are synthetic controls; no live fact producer or provenance attestation exists in this slice.",
    )


def conformance(runtime_root):
    commit = subprocess.check_output(
        ["git", "-C", str(runtime_root), "rev-parse", "HEAD"], text=True
    ).strip()
    if commit != PIN:
        raise ValueError("Runtime commit drift")
    if {p: digest(runtime_root / p) for p in RUNTIME_SOURCES} != RUNTIME_SOURCES:
        raise ValueError("Runtime source drift")
    sys.path.insert(0, str(runtime_root / "src"))
    from computer_use_mcp.core import Session
    from computer_use_mcp.contract import Node, Rect, TreeResult
    from computer_use_agent.types import (
        CallIdentity,
        DispatchCertainty,
        ImageContent,
        ToolResult,
        ToolResultStatus,
    )

    task, results, image, facts = fixture()
    node = Node(
        "synthetic-native-id",
        "Edit",
        "Document page",
        None,
        Rect(100, 100, 200, 150),
        ["enabled", "focused"],
        [],
    )
    driver = SimpleNamespace(get_tree=lambda opts: TreeResult([node], 0))
    rendered = Session(driver).ui_snapshot(scope=task["target_scope"])
    if rendered != results["snapshot"]["text"]:
        raise ValueError("Runtime snapshot format drift")
    converted = {}
    for key, row in results.items():
        result = ToolResult(
            CallIdentity("projection", "observe", row["call_id"]),
            row["tool"],
            ToolResultStatus.SUCCESS,
            DispatchCertainty.DISPATCHED,
            sanitized_text=rendered if key == "snapshot" else row["text"],
            images=(ImageContent("image/png", image, 1024, 640),)
            if key == "screenshot"
            else (),
        )
        converted[key] = dict(
            row,
            text=result.sanitized_text,
            status=result.status.value,
            dispatch=result.dispatch.value,
        )
    if project_observation(task, converted, image, facts) != project_observation(
        task, results, image, facts
    ):
        raise ValueError("Runtime projection mismatch")
    paths = [
        "src/computer_use_mcp/core.py",
        "src/computer_use_mcp/server.py",
        "src/computer_use_mcp/contract.py",
        "src/computer_use_mcp/drivers/windows.py",
        "src/computer_use_agent/types.py",
    ]
    return dict(
        commit=commit,
        sources={p: digest(runtime_root / p) for p in paths},
        session_snapshot_matched=True,
        tool_results_checked=3,
        projection_matched=True,
        driver="synthetic get_tree only",
        desktop_calls=0,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit-tests", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--runtime-root", type=Path)
    args = parser.parse_args()
    if args.unit_tests:
        checked = unittest.TextTestRunner(verbosity=1).run(
            unittest.defaultTestLoader.loadTestsFromName(
                "tests.test_gui_observation_projection"
            )
        )
        if not checked.wasSuccessful():
            raise SystemExit(1)
    if args.check or args.write_report or args.runtime_root:
        report = replay()
        if args.runtime_root:
            report["runtime"] = conformance(args.runtime_root)
            check_runtime_receipt(report["runtime"])
        if args.write_report:
            if not args.runtime_root:
                parser.error("--runtime-root required")
            REPORT.write_bytes(canonical(report))
        if args.check:
            stored = json.loads(REPORT.read_text(encoding="utf-8"))
            check_runtime_receipt(stored["runtime"])
            if not args.runtime_root:
                stored.pop("runtime")
            if stored != report:
                raise ValueError("projection report drift")
        print(
            json.dumps(
                dict(
                    valid=True,
                    missing=report["incomplete"]["missing"],
                    synthetic_projection=report["projected"]["status"],
                    negatives=len(report["negatives"]),
                    runtime_checked_now=bool(args.runtime_root),
                    desktop_executed=False,
                )
            )
        )
