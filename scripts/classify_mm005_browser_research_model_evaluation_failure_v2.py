"""Recompute or check the MM-005 Browser Research eval v2 failure classification."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_failure_classification_v2 as failure,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_protocol_v2 as protocol,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / failure.ARTIFACT_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    local = failure.verify_local_consumed_tree_if_present(ROOT)
    result = failure.build_failure_classification(ROOT)
    payload = protocol.artifact_json_bytes(result)
    output = args.output.resolve()
    if args.check:
        if (
            not output.is_file()
            or output.is_symlink()
            or output.read_bytes() != payload
        ):
            raise RuntimeError("v2 failure classification differs from recomputation")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as handle:
            handle.write(payload)
    print(
        json.dumps(
            {
                "attempt_consumed": result["claims"]["attempt_consumed"],
                "classification": result["failure"]["classification"],
                "completed_generate_calls": result["claims"][
                    "completed_generate_calls"
                ],
                "formal_gate_passed": result["formal_gate_passed"],
                "local_consumed_tree_verified": local["local_directory_present"],
                "next_gate": result["locked_next_action"]["gate_id"],
                "report_digest": result["report_digest"],
                "valid": True,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
