"""Build or check the deterministic MM-003 QLoRA training-only fixtures."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from fullcycle_bridge import mm003_post_training_protocol as contract  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "check"))
    args = parser.parse_args()

    for split, relative_path in (
        ("train", contract.TRAIN_DATASET_PATH),
        ("validation", contract.VALIDATION_DATASET_PATH),
    ):
        dataset = contract.expected_dataset(split)
        payload = contract.artifact_json_bytes(dataset)
        _write_or_check(ROOT / relative_path, payload, check=args.command == "check")
        for record in dataset["records"]:
            if record["observation_mode"] == "uia_only":
                continue
            screenshot = contract.render_training_png(record)
            path = (
                ROOT
                / contract.TRAINING_SCREENSHOT_ROOT
                / split
                / f"{record['case_id']}.png"
            )
            _write_or_check(path, screenshot, check=args.command == "check")
    print(
        {
            "train_records": contract.TRAIN_RECORDS,
            "validation_records": contract.VALIDATION_RECORDS,
            "screenshots": contract.SCREENSHOT_RECORDS,
            "valid": True,
        }
    )
    return 0


def _write_or_check(path: Path, payload: bytes, *, check: bool) -> None:
    if check:
        if not path.is_file() or path.read_bytes() != payload:
            raise RuntimeError(f"fixture differs from deterministic source: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    path.write_bytes(payload)


if __name__ == "__main__":
    raise SystemExit(main())
