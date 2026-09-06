"""Model-free checks for training isolation and assistant-only supervision."""

import hashlib
import json
import re
import unittest

from scripts.build_gui_owl_lora_pilot import CONFIG, FAMILIES, build
from scripts.probe_local_gui_executor_v2 import canonical, messages_for, score
from scripts.run_gui_owl_lora_pilot import assistant_labels
from scripts.review_gui_owl_lora_pilot import OUTPUT, review


class PilotTests(unittest.TestCase):
    def test_data_reproduces_and_gold_compiles(self):
        cfg = build()
        self.assertEqual(CONFIG.read_bytes(), canonical(cfg))
        for rows in cfg["splits"].values():
            for row in rows:
                self.assertTrue(score(row, json.dumps(row["expected"]))["task_pass"])

    def test_split_counts_and_no_prompt_overlap(self):
        splits = build()["splits"]
        self.assertEqual(
            {k: len(v) for k, v in splits.items()},
            {"train": 96, "validation": 12, "test": 24},
        )
        prompts = [canonical(messages_for(r)) for rows in splits.values() for r in rows]
        self.assertEqual(len(prompts), len(set(prompts)))
        for rows in splits.values():
            self.assertEqual({r["family"] for r in rows}, set(FAMILIES))

    def test_family_and_gold_not_added_to_prompt(self):
        for row in build()["splits"]["train"]:
            text = canonical(messages_for(row)).decode()
            self.assertNotIn('"family"', text)
            self.assertNotIn('"expected"', text)

    def test_language_attention_only(self):
        target = re.compile(build()["training"]["target_regex"])
        self.assertIsNotNone(
            target.fullmatch("model.language_model.layers.35.self_attn.q_proj")
        )
        for name in [
            "model.visual.blocks.0.attn.qkv",
            "model.language_model.layers.0.mlp.up_proj",
            "lm_head",
        ]:
            self.assertIsNone(target.fullmatch(name))

    def test_mask(self):
        self.assertEqual(assistant_labels([1, 2], [1, 2, 3, 4], 8), [-100, -100, 3, 4])

    def test_never_truncate_or_accept_bad_prefix(self):
        for prefix, full, limit in [
            ([1], [1, 2, 3], 2),
            ([1], [2, 3], 10),
            ([1], [1], 10),
        ]:
            with self.assertRaises(ValueError):
                assistant_labels(prefix, full, limit)

    def test_unsafe_training_examples_abstain(self):
        for row in build()["splits"]["train"]:
            if row["family"] in {
                "unverified",
                "ambiguous",
                "disabled",
                "background",
                "unfocused",
            }:
                self.assertEqual(row["expected"]["action"], "stop")
            if row["family"] == "stale":
                self.assertEqual(row["expected"]["action"], "observe")

    def test_retained_evidence_replays(self):
        bundle = json.loads(OUTPUT.read_text(encoding="utf-8"))
        self.assertEqual(review(bundle), bundle["summary"])

    def mutate_event(self, run_name, transform):
        bundle = json.loads(OUTPUT.read_text(encoding="utf-8"))
        run = bundle["runs"][run_name]
        events = [json.loads(line) for line in run["events_text"].splitlines()]
        transform(events)
        run["events_text"] = "".join(json.dumps(e) + "\n" for e in events)
        run["events_sha256"] = hashlib.sha256(run["events_text"].encode()).hexdigest()
        return bundle

    def test_rejects_score_promotion_even_with_updated_hash(self):
        def promote(events):
            row = next(
                e
                for e in events
                if e["event"] == "case_completed" and not e["score"]["task_pass"]
            )
            row["score"]["task_pass"] = True

        with self.assertRaisesRegex(ValueError, "score drift"):
            review(self.mutate_event("after", promote))

    def test_rejects_test_record_in_training(self):
        def leak(events):
            events[4]["ids"][0] = build()["splits"]["test"][0]["id"]

        with self.assertRaisesRegex(ValueError, "training split leakage"):
            review(self.mutate_event("train", leak))

    def test_rejects_sampling(self):
        def sample(events):
            events[2]["effective"]["do_sample"] = True

        with self.assertRaisesRegex(ValueError, "greedy config"):
            review(self.mutate_event("after", sample))

    def test_rejects_changed_prompt(self):
        def change(events):
            events[4]["rendered_prompt"] += "Additional instruction."

        with self.assertRaisesRegex(ValueError, "paired prompt mismatch"):
            review(self.mutate_event("after", change))

    def test_rejects_missing_step(self):
        def drop(events):
            del events[4]

        with self.assertRaisesRegex(ValueError, "training grammar"):
            review(self.mutate_event("train", drop))


if __name__ == "__main__":
    unittest.main()
