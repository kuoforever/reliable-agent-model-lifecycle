from __future__ import annotations

import ast
import copy
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
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_invocation_closeout as contract,
)
from fullcycle_bridge import (  # noqa: E402
    mm005_browser_research_model_evaluation_generation_failure_diagnostic_result as result_contract,
)
from scripts import (  # noqa: E402
    closeout_mm005_browser_research_model_evaluation_generation_failure_diagnostic_invocation_v1 as builder,
)


class MM005GenerationFailureDiagnosticInvocationCloseoutV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.authority_payload = (
            ROOT / result_contract.EXECUTION_AUTHORITY_PATH
        ).read_bytes()
        self.runner_payload = (ROOT / contract.RUNNER_PATH).read_bytes()
        self.recovery_io_payload = (ROOT / contract.RECOVERY_IO_PATH).read_bytes()
        self.payload = (ROOT / contract.CLOSEOUT_PATH).read_bytes()
        self.closeout = contract.parse_and_validate_invocation_closeout(
            self.payload,
            authority_payload=self.authority_payload,
            runner_payload=self.runner_payload,
            recovery_io_payload=self.recovery_io_payload,
        )

    def test_builder_reproduces_canonical_closeout(self) -> None:
        rebuilt = builder.build_closeout()
        self.assertEqual(contract.artifact_json_bytes(rebuilt), self.payload)
        self.assertEqual(json.loads(self.payload), rebuilt)
        self.assertEqual(
            self.closeout["report_digest"],
            contract.sha256_bytes(
                contract.artifact_json_bytes(
                    {
                        key: value
                        for key, value in self.closeout.items()
                        if key != "report_digest"
                    }
                )
            ),
        )

    def test_formal_invocation_is_spent_without_consuming_an_attempt(self) -> None:
        invocation = self.closeout["invocation"]
        claims = self.closeout["claims"]
        self.assertEqual(invocation["formal_invocation_budget"], 1)
        self.assertEqual(invocation["formal_invocations_observed"], 1)
        self.assertEqual(invocation["formal_invocation_budget_remaining"], 0)
        self.assertEqual(invocation["retry_budget"], 0)
        self.assertEqual(invocation["retries_observed"], 0)
        self.assertFalse(invocation["retry_authorized"])
        self.assertTrue(claims["formal_invocation_budget_spent"])
        self.assertFalse(claims["diagnostic_attempt_consumed"])
        self.assertFalse(claims["diagnostic_executed"])
        self.assertFalse(claims["model_loaded"])
        self.assertFalse(claims["cuda_workload_executed"])

    def test_zero_owner_failure_is_outside_the_frozen_terminal_grammar(self) -> None:
        grammar = self.closeout["frozen_failure_grammar"]
        self.assertEqual(len(protocol.PRE_RECORD_SESSION_PREFIXES), 6)
        self.assertTrue(
            all(
                prefix[0] == "attempt_claimed"
                for prefix in protocol.PRE_RECORD_SESSION_PREFIXES
            )
        )
        self.assertEqual(grammar["minimum_journal_event"], "attempt_claimed")
        self.assertFalse(grammar["empty_journal_representable"])
        self.assertFalse(grammar["zero_owner_failure_representable"])
        self.assertFalse(grammar["this_failure_representable"])
        self.assertFalse(grammar["terminal_synthesis_authorized"])
        self.assertIsNone(grammar["failure_scope"])
        with self.assertRaises(
            result_contract.MM005GenerationFailureDiagnosticResultError
        ):
            result_contract.select_outcome(
                protocol_and_lineage_valid=True,
                terminal_kind=None,
                failure_scope=None,
            )
        self.assertFalse(self.closeout["formal_outcome"]["selection_authorized"])
        self.assertIsNone(self.closeout["formal_outcome"]["selected_outcome"])

    def test_closeout_binds_the_exact_authority_runner_and_guard(self) -> None:
        lineage = self.closeout["lineage"]
        self.assertEqual(
            lineage["execution_authority"]["introduction_commit"],
            contract.AUTHORITY_INTRODUCTION_COMMIT,
        )
        self.assertEqual(
            lineage["execution_authority"]["parent_commit"],
            contract.AUTHORITY_PARENT_COMMIT,
        )
        self.assertTrue(
            lineage["execution_authority"]["unique_first_parent_introduction"]
        )
        for name, path, payload in (
            ("diagnostic_runner", contract.RUNNER_PATH, self.runner_payload),
            ("recovery_io", contract.RECOVERY_IO_PATH, self.recovery_io_payload),
        ):
            self.assertEqual(
                lineage[name],
                {
                    "path": path,
                    "bytes": len(payload),
                    "sha256": contract.sha256_bytes(payload),
                },
            )
        boundary = self.closeout["failure_boundary"]
        self.assertEqual(
            boundary["controller_observed_exception_type"], "RecoveryIOError"
        )
        self.assertTrue(boundary["output_parent_was_missing"])
        self.assertFalse(boundary["lifecycle_publication_entered"])
        self.assertFalse(boundary["owner_and_genesis_claim_entered"])
        self.assertFalse(boundary["terminal_handler_entered"])
        self.assertFalse(boundary["model_body_entered"])

    def test_closeout_tampering_fails_closed(self) -> None:
        for path, replacement in (
            (("invocation", "formal_invocation_budget_remaining"), 1),
            (("claims", "diagnostic_attempt_consumed"), True),
            (("formal_outcome", "selected_outcome"), "diagnostic_inconclusive"),
            (("locked_next_action", "v1_retry_authorized"), True),
        ):
            changed = copy.deepcopy(self.closeout)
            changed[path[0]][path[1]] = replacement
            with (
                self.subTest(path=path),
                self.assertRaises(
                    contract.MM005GenerationFailureDiagnosticInvocationCloseoutError
                ),
            ):
                contract.validate_invocation_closeout(
                    changed,
                    authority_payload=self.authority_payload,
                    runner_payload=self.runner_payload,
                    recovery_io_payload=self.recovery_io_payload,
                )

    def test_closeout_slice_is_exactly_ten_model_free_paths(self) -> None:
        self.assertEqual(len(contract.CLOSEOUT_SLICE_PATHS), 10)
        self.assertEqual(
            self.closeout["publication"]["slice_paths"],
            sorted(contract.CLOSEOUT_SLICE_PATHS),
        )
        self.assertFalse(self.closeout["publication"]["diagnostic_runner_modified"])
        self.assertFalse(self.closeout["publication"]["recovery_io_modified"])
        heavy = {"PIL", "bitsandbytes", "peft", "torch", "transformers"}
        for relative in (
            "src/fullcycle_bridge/mm005_browser_research_model_evaluation_"
            "generation_failure_diagnostic_invocation_closeout.py",
            "scripts/closeout_mm005_browser_research_model_evaluation_"
            "generation_failure_diagnostic_invocation_v1.py",
        ):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            imports = {
                alias.name.split(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in node.names
            }
            self.assertTrue(heavy.isdisjoint(imports), relative)

    def test_builder_check_is_read_only_and_reports_no_retry(self) -> None:
        before = self.payload
        completed = subprocess.run(
            [sys.executable, "-I", str(Path(builder.__file__)), "--check"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        summary = json.loads(completed.stdout)
        self.assertTrue(summary["formal_invocation_budget_spent"])
        self.assertEqual(summary["formal_invocation_budget_remaining"], 0)
        self.assertFalse(summary["diagnostic_attempt_consumed"])
        self.assertFalse(summary["diagnostic_executed"])
        self.assertFalse(summary["formal_outcome_selected"])
        self.assertFalse(summary["retry_authorized"])
        self.assertEqual(summary["next_gate"], contract.NEXT_GATE_ID)
        self.assertEqual((ROOT / contract.CLOSEOUT_PATH).read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
