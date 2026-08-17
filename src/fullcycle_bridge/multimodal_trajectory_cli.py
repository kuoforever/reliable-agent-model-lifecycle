"""Command-line interface for the MM-001 multimodal trajectory contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .multimodal_trajectory import (
    TrajectoryValidationError,
    validate_trajectory_file,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate one synthetic MM-001 multimodal trajectory fixture."
    )
    parser.add_argument("--trajectory", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = validate_trajectory_file(args.trajectory.resolve(strict=False))
    except TrajectoryValidationError as exc:
        print(
            json.dumps(
                {
                    "valid": False,
                    "code": exc.code,
                    "location": exc.location,
                    "detail": exc.detail,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=__import__("sys").stderr,
        )
        return 2
    result = {"valid": True, **summary.to_dict()}
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
