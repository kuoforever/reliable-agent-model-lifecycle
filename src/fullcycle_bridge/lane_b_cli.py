"""Offline CLI for one Lane B consent/capture/deletion review bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .lane_b import LaneBValidationError, validate_bundle_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = validate_bundle_file(args.bundle.resolve(strict=True))
    except (LaneBValidationError, OSError) as exc:
        if isinstance(exc, LaneBValidationError):
            payload = {
                "valid": False,
                "code": exc.code,
                "location": exc.location,
                "detail": exc.detail,
            }
        else:
            payload = {
                "valid": False,
                "code": "UNSAFE_INPUT_FILE",
                "location": str(args.bundle),
                "detail": str(exc),
            }
        print(
            json.dumps(payload, sort_keys=True, separators=(",", ":")), file=sys.stderr
        )
        return 2
    print(
        json.dumps(
            {"valid": True, **summary.to_dict()},
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
