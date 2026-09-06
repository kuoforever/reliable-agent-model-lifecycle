"""Deterministic synthetic contract adaptation data; no desktop captures."""

from __future__ import annotations

import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.probe_local_gui_executor_v2 import canonical, messages_for, score  # noqa: E402

FAMILIES = (
    "focus",
    "write",
    "read",
    "save",
    "activate",
    "stale",
    "unverified",
    "ambiguous",
    "disabled",
    "background",
    "unfocused",
    "reordered",
)
CONFIG = ROOT / "configs/gui_owl_lora_pilot_v1.json"


def examples(seed, repeats):
    rng = random.Random(seed)
    rows = []
    for family in FAMILIES:
        for _ in range(repeats):
            identity = f"task-{rng.getrandbits(48):012x}"
            scope = str(rng.randrange(10000, 999999))
            epoch = rng.randrange(10, 900)
            label = f"Document {rng.randrange(1000, 9999)} content"
            ref = rng.randrange(100, 900000)
            control = dict(
                ref=f"ref_{ref}",
                role="edit",
                name=label,
                enabled=family != "disabled",
                focused=family != "unfocused",
            )
            controls = [
                control,
                dict(
                    ref=f"ref_{ref + 1}",
                    role="edit",
                    name="Search",
                    enabled=True,
                    focused=False,
                ),
            ]
            kind = {
                "write": "write_brief",
                "background": "write_brief",
                "unfocused": "write_brief",
                "read": "read_source",
                "save": "save_word",
                "unverified": "save_word",
                "activate": "activate_target",
            }.get(family, "focus_editor")
            goal = {"kind": kind}
            if kind in {"focus_editor", "write_brief"}:
                goal["target_label"] = label
            if kind == "write_brief":
                goal["text"] = (
                    f"The public report lists {rng.randrange(10, 90)} completed tasks."
                )
            if family == "ambiguous":
                controls.append(dict(control, ref=f"ref_{ref + 2}"))
            rng.shuffle(controls)
            request = dict(
                version=1,
                request_id=identity,
                target_scope=scope,
                current_epoch=epoch,
                runtime_generation=rng.randrange(1, 100),
                subgoal=goal,
                observation=dict(
                    scope=scope,
                    epoch=epoch - (family == "stale"),
                    foreground_scope=str(int(scope) + 1)
                    if family in {"background", "activate"}
                    else scope,
                    controls=controls,
                    text=f"Public briefing {rng.randrange(100, 9999)}.",
                    text_verified=family != "unverified",
                ),
            )
            action = {
                "focus_editor": "click_ref",
                "write_brief": "type_text",
                "read_source": "read_text",
                "save_word": "save",
                "activate_target": "activate",
            }[kind]
            if family == "stale":
                action = "observe"
            elif family in {
                "unverified",
                "ambiguous",
                "disabled",
                "background",
                "unfocused",
            }:
                action = "stop"
            expected = dict(request_id=identity, observation_epoch=epoch, action=action)
            if action in {"click_ref", "type_text"}:
                expected["ref"] = control["ref"]
            row = dict(
                id=identity,
                family=family,
                group="contract",
                request=request,
                expected=expected,
            )
            if not score(row, json.dumps(expected))["task_pass"]:
                raise ValueError("INVALID_GOLD")
            rows.append(row)
    rng.shuffle(rows)
    return rows


def build():
    splits = {
        "train": examples(613, 8),
        "validation": examples(719, 1),
        "test": examples(823, 2),
    }
    prompts = [canonical(messages_for(c)) for rows in splits.values() for c in rows]
    if len(set(prompts)) != len(prompts):
        raise ValueError("DUPLICATE_PROMPT")
    return dict(
        id="FC-MVP-002-gui-owl-lora-pilot-v1",
        model_id="mPLUG/GUI-Owl-1.5-4B-Instruct",
        revision="3f061c2c562cc860c42bf32542a70e07a7ff4840",
        splits=splits,
        training=dict(
            seed=41,
            steps=48,
            accumulation=4,
            batch_size=1,
            max_tokens=1024,
            learning_rate=0.0002,
            warmup_steps=4,
            rank=8,
            alpha=16,
            dropout=0.0,
            target_regex=r"model\.language_model\.layers\.\d+\.self_attn\.(q_proj|v_proj)",
            dtype="bfloat16",
            gradient_checkpointing=True,
            max_seconds=1800,
            max_allocated_bytes=15000000000,
        ),
        selection="Fixed final step only; validation loss diagnostic; test never selects checkpoint.",
        rubric=dict(
            fresh_exact_min=20,
            fresh_gain_min=8,
            visual_exact_min=8,
            limits="Same synthetic rule families across splits; not OOD or live reliability.",
        ),
    )


if __name__ == "__main__":
    CONFIG.write_bytes(canonical(build()))
