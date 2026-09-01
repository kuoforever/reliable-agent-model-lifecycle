from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic as protocol,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_result as contract,
)
from scripts import (  # noqa: E402
    prepare_mm005_browser_research_model_evaluation_generation_failure_diagnostic_execution_authority_v1 as builder,
)


class MM005GenerationFailureDiagnosticExecutionAuthorityV1Tests(unittest.TestCase):
    def test_builder_reproduces_canonical_authority(self) -> None:
        payload = (ROOT / contract.EXECUTION_AUTHORITY_PATH).read_bytes()
        authority = builder.build_authority()
        self.assertEqual(contract.artifact_json_bytes(authority), payload)
        self.assertEqual(json.loads(payload), authority)

    def test_authority_binds_exact_implementation_environment_and_budgets(self) -> None:
        authority = builder.build_authority()
        self.assertEqual(
            authority["implementation_freeze_commit"],
            builder.IMPLEMENTATION_FREEZE_COMMIT,
        )
        self.assertEqual(authority["gate_id"], contract.EXECUTION_AUTHORITY_GATE_ID)
        self.assertEqual(authority["next_gate"], contract.EXECUTION_GATE_ID)
        self.assertEqual(
            authority["budgets"],
            {
                "formal_invocations": 1,
                "per_record_attempts": 1,
                "retries": 0,
            },
        )
        environment = authority["resource_preflight"]["expected_environment"]
        self.assertEqual(set(environment), set(protocol.OBSERVED_ENVIRONMENT_FIELDS))
        self.assertTrue(all(value != "" for value in environment.values()))
        self.assertEqual(
            authority["claims"],
            {
                "authority_frozen": True,
                "diagnostic_attempt_consumed": False,
                "diagnostic_executed": False,
                "model_evaluated": False,
                "runtime_eligible": False,
            },
        )

    def test_dependency_receipts_match_current_files(self) -> None:
        authority = builder.build_authority()
        receipts = authority["critical_execution_dependency_receipts"]
        self.assertEqual(
            set(receipts), set(contract.CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS)
        )
        for name, relative in sorted(
            contract.CRITICAL_EXECUTION_DEPENDENCY_SOURCE_PATHS.items()
        ):
            payload = (ROOT / relative).read_bytes()
            self.assertEqual(
                receipts[name],
                {
                    "path": relative,
                    "bytes": len(payload),
                    "sha256": contract.sha256_bytes(payload),
                },
            )

    def test_authority_slice_is_exactly_ten_paths(self) -> None:
        self.assertEqual(len(contract.EXECUTION_AUTHORITY_SLICE_PATHS), 10)
        self.assertIn(
            contract.EXECUTION_AUTHORITY_PATH, contract.EXECUTION_AUTHORITY_SLICE_PATHS
        )
        self.assertIn(
            "scripts/prepare_mm005_browser_research_model_evaluation_generation_"
            "failure_diagnostic_execution_authority_v1.py",
            contract.EXECUTION_AUTHORITY_SLICE_PATHS,
        )
        self.assertIn(
            "tests/test_mm005_browser_research_model_evaluation_generation_failure_"
            "diagnostic_execution_authority.py",
            contract.EXECUTION_AUTHORITY_SLICE_PATHS,
        )

    def test_builder_check_is_read_only_and_reports_unconsumed_authority(self) -> None:
        before = (ROOT / contract.EXECUTION_AUTHORITY_PATH).read_bytes()
        completed = subprocess.run(
            [sys.executable, "-I", str(Path(builder.__file__)), "--check"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        summary = json.loads(completed.stdout)
        self.assertTrue(summary["authority_frozen"])
        self.assertFalse(summary["diagnostic_attempt_consumed"])
        self.assertFalse(summary["diagnostic_executed"])
        self.assertEqual(summary["next_gate"], contract.EXECUTION_GATE_ID)
        self.assertEqual(
            (ROOT / contract.EXECUTION_AUTHORITY_PATH).read_bytes(), before
        )


if __name__ == "__main__":
    unittest.main()
