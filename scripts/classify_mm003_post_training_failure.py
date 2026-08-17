"""Recompute or check the MM-003 QLoRA v1 failure classification."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from fullcycle_bridge import mm003_post_training_failure_classification as failure  # noqa: E402
from fullcycle_bridge import mm003_post_training_protocol as protocol  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / failure.ARTIFACT_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    local_receipt = ROOT / failure.LOCAL_FAILURE_RECEIPT_PATH
    if not args.check or local_receipt.exists():
        failure.verify_local_failure_receipt(ROOT)
    result = failure.build_failure_classification(ROOT)
    payload = protocol.artifact_json_bytes(result)
    output = args.output.resolve()
    if args.check:
        if not output.is_file() or output.is_symlink() or output.read_bytes() != payload:
            raise RuntimeError("failure classification differs from recomputation")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as handle:
            handle.write(payload)
    print(
        json.dumps(
            {
                "failed_gate_id": result["failed_gate_id"],
                "formal_gate_passed": result["formal_gate_passed"],
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
