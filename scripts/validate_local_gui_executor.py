"""Validate synthetic executor controls without a model or desktop dispatch."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/local_gui_executor_v1/cases.json"
SOURCES = [
    "src/fullcycle_bridge/local_gui_executor.py",
    "fixtures/local_gui_executor_v1/cases.json",
    "scripts/validate_local_gui_executor.py",
]


def receipt(path: Path) -> dict:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def conformance(runtime_root: Path) -> dict:
    from fullcycle_bridge.local_gui_executor import (
        ExecutorContractError,
        compile_response,
        model_request,
    )

    sys.path.insert(0, str(runtime_root / "src"))
    from computer_use_agent.tool_registry import validate_tool_arguments

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = []
    for case in fixture["cases"]:
        try:
            compiled = compile_response(
                case["request"], case["current_request"], json.dumps(case["response"])
            )
        except ExecutorContractError as exc:
            if case["expected"] != {"error": str(exc)}:
                raise ValueError("unexpected contract rejection") from exc
            rows.append({"id": case["id"], "rejected": str(exc)})
        else:
            value = compiled.to_dict()
            if {"tool": value["tool"], "arguments": value["arguments"]} != case[
                "expected"
            ]:
                raise ValueError("unexpected compiled proposal")
            if compiled.tool is not None:
                validate_tool_arguments(compiled.tool, dict(compiled.arguments))
            rows.append(
                {
                    "id": case["id"],
                    "compiled": value,
                    "runtime_argument_schema_checked": compiled.tool is not None,
                }
            )
    projection = {
        case["id"]: model_request(case["request"]) for case in fixture["cases"]
    }
    return {
        "id": "FC-MVP-002-local-gui-executor-contract-v1",
        "valid": True,
        "source_receipts": {name: receipt(ROOT / name) for name in SOURCES},
        "runtime": {
            "commit": subprocess.check_output(
                ["git", "-C", str(runtime_root), "rev-parse", "HEAD"], text=True
            ).strip(),
            "tool_registry": receipt(
                runtime_root / "src/computer_use_agent/tool_registry.py"
            ),
        },
        "case_count": len(rows),
        "runtime_argument_checks": sum(
            row.get("runtime_argument_schema_checked", False) for row in rows
        ),
        "expected_rejections": sum("rejected" in row for row in rows),
        "stop_proposals": sum(
            row.get("compiled", {}).get("action") == "stop" for row in rows
        ),
        "model_projection_sha256": hashlib.sha256(
            json.dumps(projection, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest(),
        "cases": rows,
        "model_evaluated": False,
        "desktop_executed": False,
        "runtime_authorization_checked": False,
        "serving_eligible": False,
    }


def main() -> int:
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT))
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit-tests", action="store_true")
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--check-report", type=Path)
    args = parser.parse_args()
    if args.unit_tests:
        if args.runtime_root or args.check_report:
            parser.error("unit tests are independent of Runtime checkout/report")
        suite = unittest.defaultTestLoader.loadTestsFromNames(
            [
                "tests.test_local_gui_executor",
                "tests.test_local_desktop_readiness_probe",
            ]
        )
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        return int(not result.wasSuccessful())
    if args.runtime_root is None:
        parser.error("--runtime-root required for read-only schema conformance")
    report = conformance(args.runtime_root)
    payload = (
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode()
    if args.check_report:
        if args.check_report.read_bytes() != payload:
            raise ValueError("retained conformance report drift")
        print(
            json.dumps(
                {
                    "valid": True,
                    "case_count": report["case_count"],
                    "runtime_argument_checks": report["runtime_argument_checks"],
                }
            )
        )
    else:
        sys.stdout.buffer.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
