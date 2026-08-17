"""Command-line interface for the MM-002 GUI grounding evaluation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from fullcycle_bridge.gui_grounding_eval import (
    GuiGroundingValidationError,
    load_suite_file,
    score_files,
    validate_suite,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fullcycle-gui-grounding-eval")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("suite", type=Path)
    score_parser = subparsers.add_parser("score")
    score_parser.add_argument("suite", type=Path)
    score_parser.add_argument("predictions", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            result = {
                "valid": True,
                **validate_suite(load_suite_file(args.suite.resolve())).to_dict(),
            }
        else:
            result = {
                "valid": True,
                **score_files(args.suite.resolve(), args.predictions.resolve()),
            }
    except (GuiGroundingValidationError, OSError) as exc:
        code = exc.code if isinstance(exc, GuiGroundingValidationError) else "IO_ERROR"
        print(
            json.dumps(
                {"valid": False, "error": code, "message": str(exc)}, sort_keys=True
            ),
            file=sys.stderr,
        )
        return 2
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
