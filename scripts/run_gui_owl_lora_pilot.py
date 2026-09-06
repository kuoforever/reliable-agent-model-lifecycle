"""Local BF16 LoRA pilot with fresh-load evaluation and durable event evidence."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import random
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_gui_owl_lora_pilot import CONFIG, examples  # noqa: E402
from scripts.probe_local_gui_executor_v2 import (  # noqa: E402
    canonical,
    digest,
    messages_for,
    score,
    source_receipts,
    summarize,
)


def assistant_labels(prefix, complete, limit):
    if len(complete) > limit:
        raise ValueError("TRAIN_TOKEN_CAP")
    if complete[: len(prefix)] != prefix or len(complete) <= len(prefix):
        raise ValueError("ASSISTANT_PREFIX_MISMATCH")
    return [-100] * len(prefix) + complete[len(prefix) :]


def receipts():
    regression = json.loads(
        (ROOT / "configs/local_gui_executor_probe_v2.json").read_text()
    )
    result = source_receipts(regression)
    for path in [CONFIG, Path(__file__), ROOT / "scripts/build_gui_owl_lora_pilot.py"]:
        result[path.relative_to(ROOT).as_posix()] = dict(
            sha256=digest(path), bytes=path.stat().st_size
        )
    return result


def run(args):
    for key in ["HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"]:
        os.environ[key] = "1"
    import torch
    from PIL import Image
    from peft import LoraConfig, PeftModel, get_peft_model
    from transformers import (
        AutoProcessor,
        GenerationConfig,
        Qwen3VLForConditionalGeneration,
    )

    cfg = json.loads(CONFIG.read_text())
    hp = cfg["training"]
    args.output.mkdir(parents=True, exist_ok=False)
    stream = (args.output / "events.jsonl").open("x", encoding="utf-8", newline="\n")
    start = time.monotonic()

    def record(event, **data):
        stream.write(
            json.dumps(
                dict(event=event, elapsed_seconds=time.monotonic() - start, **data),
                ensure_ascii=False,
            )
            + "\n"
        )
        stream.flush()
        os.fsync(stream.fileno())
        print(event, data.get("step", data.get("id", "")), flush=True)

    def cap():
        if torch.cuda.max_memory_allocated() > hp["max_allocated_bytes"]:
            raise ValueError("MEMORY_CAP")
        if time.monotonic() - start > hp["max_seconds"]:
            raise ValueError("TIME_CAP")

    try:
        sources = receipts()
        model_files = {
            p.name: digest(p) for p in sorted(args.model.glob("*")) if p.is_file()
        }
        expected_weights = {
            "model-00001-of-00002.safetensors": "03c36699f9437d781a6d4d418afe69ce2e198947c234819b41a10e8c29cf7ea4",
            "model-00002-of-00002.safetensors": "31e6c27c212658b5faea4a72442047a5ce8d4fbd409b775fa18752fb5a20ea09",
        }
        if any(model_files.get(k) != v for k, v in expected_weights.items()):
            raise ValueError("BASE_WEIGHT_MISMATCH")
        plan = dict(
            mode=args.mode,
            config_sha256=digest(CONFIG),
            sources=sources,
            model_files=model_files,
            model_id=cfg["model_id"],
            revision=cfg["revision"],
            environment={
                n: importlib.metadata.version(n)
                for n in ["torch", "transformers", "peft", "accelerate", "tokenizers"]
            },
            python=sys.version,
            training=hp,
            device=torch.cuda.get_device_name(),
            adapter_files={
                p.name: digest(p) for p in sorted(args.adapter.glob("*")) if p.is_file()
            }
            if args.adapter
            else None,
        )
        (args.output / "plan.json").write_bytes(canonical(plan))
        random.seed(hp["seed"])
        torch.manual_seed(hp["seed"])
        torch.cuda.manual_seed_all(hp["seed"])
        torch.set_num_threads(4)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.cuda.reset_peak_memory_stats()
        record("load_started")
        model = Qwen3VLForConditionalGeneration.from_pretrained(
            args.model,
            dtype=torch.bfloat16,
            attn_implementation="sdpa",
            device_map={"": 0},
            local_files_only=True,
            trust_remote_code=False,
        )
        processor = AutoProcessor.from_pretrained(
            args.model, local_files_only=True, trust_remote_code=False
        )
        processor.image_processor.size = {
            "shortest_edge": 65536,
            "longest_edge": 655360,
        }
        record("load_completed")

        def tokenize(case):
            messages = messages_for(case)
            prefix = processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            full = processor.apply_chat_template(
                messages
                + [
                    {
                        "role": "assistant",
                        "content": json.dumps(case["expected"], sort_keys=True),
                    }
                ],
                tokenize=False,
                add_generation_prompt=False,
            )
            prefix_ids = processor.tokenizer(prefix, add_special_tokens=False)[
                "input_ids"
            ]
            ids = processor.tokenizer(full, add_special_tokens=False)["input_ids"]
            labels = assistant_labels(prefix_ids, ids, hp["max_tokens"])
            return dict(
                input_ids=torch.tensor([ids], device="cuda"),
                attention_mask=torch.ones(
                    (1, len(ids)), dtype=torch.long, device="cuda"
                ),
                labels=torch.tensor([labels], device="cuda"),
            )

        if args.mode in {"preflight", "train"}:
            model = get_peft_model(
                model,
                LoraConfig(
                    r=hp["rank"],
                    lora_alpha=hp["alpha"],
                    lora_dropout=hp["dropout"],
                    target_modules=hp["target_regex"],
                    bias="none",
                    task_type="CAUSAL_LM",
                ),
            )
            trainable = {
                name: dict(shape=list(p.shape), dtype=str(p.dtype), numel=p.numel())
                for name, p in model.named_parameters()
                if p.requires_grad
            }
            if not trainable or any(
                "lora_" not in n or ".language_model.layers." not in n
                for n in trainable
            ):
                raise ValueError("TRAINABLE_BOUNDARY")
            record(
                "adapter_configured",
                trainable=trainable,
                trainable_parameters=sum(v["numel"] for v in trainable.values()),
            )
            model.config.use_cache = False
            model.gradient_checkpointing_enable(
                gradient_checkpointing_kwargs={"use_reentrant": False}
            )
            model.enable_input_require_grads()
            model.train()
            optimizer = torch.optim.AdamW(
                [p for p in model.parameters() if p.requires_grad],
                lr=hp["learning_rate"],
                weight_decay=0.0,
            )
            data = (
                examples(997, 1)[:4]
                if args.mode == "preflight"
                else cfg["splits"]["train"]
            )
            tokenized = [tokenize(c) for c in data]
            record(
                "tokenized",
                records=len(data),
                max_tokens=max(v["input_ids"].shape[1] for v in tokenized),
                supervised_tokens=[int((v["labels"] != -100).sum()) for v in tokenized],
            )
            order = list(range(len(data)))
            rng = random.Random(hp["seed"])
            rng.shuffle(order)
            cursor = 0
            steps = 1 if args.mode == "preflight" else hp["steps"]
            for step in range(1, steps + 1):
                cap()
                lr = (
                    hp["learning_rate"]
                    * min(step / hp["warmup_steps"], 1)
                    * max(
                        (hp["steps"] - step + 1) / (hp["steps"] - hp["warmup_steps"]), 0
                    )
                    if step > hp["warmup_steps"]
                    else hp["learning_rate"] * step / hp["warmup_steps"]
                )
                for group in optimizer.param_groups:
                    group["lr"] = lr
                optimizer.zero_grad(set_to_none=True)
                losses = []
                indices = []
                for _ in range(hp["accumulation"]):
                    if cursor == len(order):
                        rng.shuffle(order)
                        cursor = 0
                    idx = order[cursor]
                    cursor += 1
                    loss = model(**tokenized[idx]).loss
                    if not torch.isfinite(loss):
                        raise ValueError("NONFINITE_LOSS")
                    losses.append(loss.item())
                    indices.append(data[idx]["id"])
                    (loss / hp["accumulation"]).backward()
                norm = torch.nn.utils.clip_grad_norm_(
                    model.parameters(), 1.0, error_if_nonfinite=True
                )
                if float(norm) <= 0:
                    raise ValueError("ZERO_GRADIENT")
                optimizer.step()
                torch.cuda.synchronize()
                record(
                    "optimizer_step",
                    step=step,
                    loss=sum(losses) / len(losses),
                    learning_rate=lr,
                    gradient_norm=float(norm),
                    ids=indices,
                    peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                )
            cap()
            model.eval()
            if args.mode == "train":
                with torch.no_grad():
                    values = [
                        float(model(**tokenize(c)).loss)
                        for c in cfg["splits"]["validation"]
                    ]
                record(
                    "validation_loss", loss=sum(values) / len(values), count=len(values)
                )
                model.save_pretrained(args.output / "adapter", safe_serialization=True)
                record(
                    "adapter_saved",
                    files={
                        p.name: digest(p)
                        for p in sorted((args.output / "adapter").glob("*"))
                        if p.is_file()
                    },
                )
        else:
            if args.adapter:
                model = PeftModel.from_pretrained(
                    model, args.adapter, is_trainable=False, local_files_only=True
                )
            model.eval()
            model.config.use_cache = True
            generation = GenerationConfig(
                max_new_tokens=192,
                do_sample=False,
                num_beams=1,
                max_time=45,
                eos_token_id=model.generation_config.eos_token_id,
                pad_token_id=processor.tokenizer.pad_token_id,
                use_cache=True,
            )
            effective, _ = model._prepare_generation_config(
                generation, use_model_defaults=False, do_sample=False
            )
            if effective.do_sample or effective.num_beams != 1:
                raise ValueError("GREEDY_CONFIGURATION_NOT_EFFECTIVE")
            record("generation_configured", effective=effective.to_dict())
            old = json.loads(
                (ROOT / "configs/local_gui_executor_probe_v2.json").read_text()
            )["cases"]
            rows = []
            for case in cfg["splits"]["test"] + old:
                cap()
                record("case_started", id=case["id"])
                prompt = processor.apply_chat_template(
                    messages_for(case), tokenize=False, add_generation_prompt=True
                )
                image = (
                    Image.open(ROOT / case["image"]).convert("RGB")
                    if case["group"] == "visual"
                    else None
                )
                inputs = processor(
                    text=[prompt],
                    images=[image] if image else None,
                    return_tensors="pt",
                ).to("cuda")
                count = inputs.input_ids.shape[1]
                if count > 4096:
                    raise ValueError("EVAL_TOKEN_CAP")
                torch.cuda.synchronize()
                began = time.monotonic()
                with torch.inference_mode():
                    output = model.generate(
                        **inputs,
                        generation_config=generation,
                        use_model_defaults=False,
                        do_sample=False,
                    )
                torch.cuda.synchronize()
                seconds = time.monotonic() - began
                tokens = output[0, count:].tolist()
                raw = processor.decode(
                    tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False
                )
                row = dict(
                    id=case["id"],
                    group=case["group"],
                    cohort="fresh" if case in cfg["splits"]["test"] else "regression",
                    raw_output=raw,
                    token_ids=tokens,
                    input_tokens=count,
                    rendered_prompt=prompt,
                    generation_seconds=seconds,
                    score=score(case, raw),
                )
                record("case_completed", **row)
                rows.append(row)
            record(
                "evaluation_completed",
                cohorts={
                    key: summarize([r for r in rows if r["cohort"] == key])
                    for key in ["fresh", "regression"]
                },
            )
        cap()
        if receipts() != sources:
            raise ValueError("SOURCE_DRIFT")
        if any(digest(args.model / name) != sha for name, sha in model_files.items()):
            raise ValueError("BASE_FILE_DRIFT")
        record(
            "completed",
            peak_allocated_bytes=torch.cuda.max_memory_allocated(),
            plan_sha256=digest(args.output / "plan.json"),
        )
    except BaseException:
        (args.output / "failure.txt").write_text(
            traceback.format_exc(), encoding="utf-8"
        )
        record("failed")
        raise
    finally:
        stream.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["preflight", "train", "eval"])
    parser.add_argument(
        "--model", type=Path, default=ROOT / "work/gui-probe-v2/models/gui-owl"
    )
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
